"""Reseau RECUPERATION (rappel) : l'hippocampe du systeme.

Repond depuis un corpus de paires question/reponse DEJA VALIDEES, par recherche lexicale
PONDEREE PAR LA RARETE (IDF, comme BM25). Matcher un mot RARE et discriminant ("Zeus",
"Pixar", "photosynthese") pese fort ; matcher un mot FREQUENT et banal ("demain", "fais",
"chose") pese peu -> on ne se laisse plus piéger par un recouvrement incident sur des mots
outils. Il RECITE la reponse stockee -- il ne la reformule JAMAIS avec le modele -- donc sur le
chemin "trouve", l'hallucination est structurellement impossible (on recite une chaine deja
verifiee). Sous `min_score`, il DECLINE (None) : on prefere l'aveu d'ignorance a une fausse
memoire confiante. `confidence` = score du meilleur match -> le routeur peut durcir via son seuil.

Ancrage : recuperation lexicale ponderee (BM25 / IDF), plus-proche-voisin (kNN-LM 2020),
abstention par seuil (Chow 1970), separation memoire/poids (CLS, McClelland 1995). 100%
deterministe, local, auditable -- fidele a l'ADN de CybNodes.

    from cybnodes.networks import RecallNetwork
    net = RecallNetwork(pairs=[("c'est quoi pixar ?", "Pixar, c'est un studio d'animation.")])
    net.match("c'est quoi Pixar")   # -> Result(text="Pixar...", confidence=...)
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

from ..network import Manifest, Network
from ..result import Result

# Mots-outils francais par defaut (surchargeables). On retire le bruit pour comparer le SENS.
_STOP = frozenset((
    "le la les un une des de du et ou au aux en dans ce cet cette ces mon ma mes ton ta tes "
    "son sa ses que qui quel quelle quels quelles est cest tu je il elle on se ne pas plus pour "
    "par sur avec ca quoi comment pourquoi quand combien y me te nous vous ils elles a l c s d n"
).split())


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _edist(a: str, b: str, maxd: int) -> int:
    """Distance d'edition (Levenshtein) BORNEE : renvoie la distance, ou maxd+1 si > maxd (early-exit)."""
    la, lb = len(a), len(b)
    if abs(la - lb) > maxd:
        return maxd + 1
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i]
        row_min = i
        ai = a[i - 1]
        for j in range(1, lb + 1):
            c = prev[j - 1] if ai == b[j - 1] else prev[j - 1] + 1
            if prev[j] + 1 < c:
                c = prev[j] + 1
            if cur[j - 1] + 1 < c:
                c = cur[j - 1] + 1
            cur.append(c)
            if c < row_min:
                row_min = c
        if row_min > maxd:
            return maxd + 1
        prev = cur
    return prev[lb]


# Un Scorer compare deux ensembles de tokens (requete, document) -> 0..1. Si fourni, il REMPLACE
# le score IDF interne (utile pour brancher une similarite vectorielle/embeddings plus tard).
Scorer = Callable[[Set[str], Set[str]], float]


class RecallNetwork(Network):
    """Recuperation lexicale ponderee par la rarete (IDF) dans un corpus de Q/R validees.
    Recite la reponse, ne la reformule pas. Decline sous le seuil (abstention honnete)."""

    name = "savoir"
    manifest = Manifest(
        answers="reponses recitees depuis un corpus de questions/reponses validees (recuperation lexicale ponderee IDF)",
        deterministic=True,
        needs_source=True,
        fallback="pass",
    )

    def __init__(self,
                 pairs: Optional[Sequence[Sequence]] = None,
                 min_score: float = 0.5,
                 min_weight: float = 0.0,
                 stopwords: Optional[Sequence[str]] = None,
                 synonyms: Optional[Dict[str, str]] = None,
                 scorer: Optional[Scorer] = None,
                 fuzzy: bool = True,
                 source_label: str = "memoire validee"):
        """pairs : suite de (question, reponse) ou (question, reponse, source).

        min_score  : score relatif minimal (part du poids de la requete couverte).
        min_weight : INFORMATION absolue minimale des mots partages (somme d'IDF). Coupe les
                     matchs sur des mots trop banals : "je t'aime" (mot frequent "aime") est
                     rejete, "c'est quoi Pixar" (mot rare "pixar") passe. 0.0 = desactive.
        """
        self.min_score = float(min_score)
        self.min_weight = float(min_weight)
        self.stop = frozenset(stopwords) if stopwords is not None else _STOP
        self.syn = dict(synonyms or {})
        self.scorer: Optional[Scorer] = scorer
        self.fuzzy = bool(fuzzy)
        self.source_label = source_label
        self._index: List[Tuple[str, Optional[str], Set[str]]] = []
        self._df: Dict[str, int] = {}        # frequence documentaire par token
        self._idf: Dict[str, float] = {}     # poids de rarete (recalcule a chaque ajout)
        self._idf_default = 0.0
        if pairs:
            self.add_pairs(pairs)

    def _tok(self, s: str) -> Set[str]:
        return {self.syn.get(w, w) for w in re.findall(r"[a-z0-9]+", _norm(s))
                if len(w) > 1 and w not in self.stop}

    def _correct(self, w: str) -> str:
        """Corrige un token de REQUETE vers le token du corpus le plus proche (faute de frappe <= 1/2).
        Un token deja connu (ou < 4 lettres) est renvoye tel quel -> ZERO regression sur une requete propre."""
        if not self.fuzzy or len(w) < 4 or w in self._df:
            return w
        maxd = 2 if len(w) >= 8 else 1
        best, bestd = w, maxd + 1
        for v in self._df:
            if abs(len(v) - len(w)) > maxd:
                continue
            d = _edist(w, v, maxd)
            if d < bestd:
                bestd, best = d, v
                if d == 1:
                    break
        return best if bestd <= maxd else w

    def _qtok(self, s: str) -> Set[str]:
        """Tokens de REQUETE avec correction des fautes vers le vocab du corpus (robustesse typo)."""
        return {self._correct(t) for t in self._tok(s)}

    def _recompute_idf(self) -> None:
        n = max(1, len(self._index))
        # IDF lisse : un token present partout pese ~0, un token rare pese fort.
        self._idf = {t: math.log(1.0 + n / (1.0 + c)) for t, c in self._df.items()}
        self._idf_default = math.log(1.0 + n)   # token inconnu du corpus = traite comme rare

    def _w(self, t: str) -> float:
        return self._idf.get(t, self._idf_default)

    def add_pairs(self, pairs: Sequence[Sequence]) -> "RecallNetwork":
        """Ajoute des paires (la memoire qui GRANDIT : non-parametrique, reversible)."""
        for p in pairs:
            q, a = p[0], p[1]
            src = p[2] if len(p) > 2 else None
            qt = self._tok(q)
            if qt and a:
                self._index.append((a, src, qt))
                for t in qt:
                    self._df[t] = self._df.get(t, 0) + 1
        self._recompute_idf()
        return self

    def match(self, question: str) -> Optional[Result]:
        qt = self._qtok(question)
        if not qt:
            return None
        use_idf = self.scorer is None
        qw = sum(self._w(t) for t in qt) if use_idf else 0.0
        best, best_a, best_src, best_key = 0.0, None, None, None
        for ans, src, dt in self._index:
            if use_idf:
                shared = qt & dt
                if not shared:
                    continue
                sc = (sum(self._w(t) for t in shared) / qw) if qw else 0.0
                # departage des EX-AEQUO de couverture par Jaccard : prefere le match le plus
                # SERRE (question du gold la plus centree sur la requete). Mesure : +6.3 pts
                # d'exactitude, corrige les requetes courtes ("Athena" -> deesse, pas Parthenon).
                key = (sc, len(shared) / len(qt | dt))
            else:
                sc = self.scorer(qt, dt)
                key = (sc, 0.0)
            if best_key is None or key > best_key:
                best, best_a, best_src, best_key = sc, ans, src, key
        if best_a is None or best < self.min_score:
            return None  # rien d'assez sur -> on passe la main (abstention)
        if use_idf and self.min_weight > 0.0 and (best * qw) < self.min_weight:
            return None  # match sur des mots trop banals (faible information) -> abstention
        return Result(
            kind="savoir",
            text=best_a,
            data={"score": round(best, 3)},
            source=(best_src or self.source_label),
            confidence=round(min(1.0, best), 3),
        )

    def match_topk(self, question: str, k: int = 3):
        """Les k meilleurs golds candidats au-dessus de min_score, score decroissant :
        [(score, reponse, source), ...]. Prerequis de l'arbitrage : voir si plusieurs golds
        PROCHES se contredisent (desaccord interne au corpus, sans aucun LLM ni 2e canal)."""
        qt = self._qtok(question)
        if not qt:
            return []
        use_idf = self.scorer is None
        qw = sum(self._w(t) for t in qt) if use_idf else 0.0
        scored = []
        for ans, src, dt in self._index:
            if use_idf:
                shared = qt & dt
                if not shared:
                    continue
                sc = (sum(self._w(t) for t in shared) / qw) if qw else 0.0
                tie = len(shared) / len(qt | dt)   # meme departage Jaccard qu'en match()
            else:
                sc = self.scorer(qt, dt)
                tie = 0.0
            if sc >= self.min_score:
                scored.append((sc, tie, round(min(1.0, sc), 3), ans, (src or self.source_label)))
        scored.sort(key=lambda x: (-x[0], -x[1]))     # score puis serrage (ex-aequo)
        return [(s[2], s[3], s[4]) for s in scored[:k]]

    def __len__(self) -> int:
        return len(self._index)

    def __repr__(self) -> str:  # pragma: no cover
        return "<RecallNetwork %d paires>" % len(self._index)
