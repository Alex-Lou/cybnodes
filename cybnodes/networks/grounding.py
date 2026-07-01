"""Gate d'ANCRAGE (grounding) : une derniere verification avant de servir une reponse recuperee.

Meme a score eleve, un match lexical peut repondre A COTE : "le sang, c'est quoi ?" attrape un gold
sur LE COEUR qui pompe le sang -- score haut, sujet faux. Le score seul ne separe pas ces cas :
l'erreur est SEMANTIQUE, pas lexicale (mesure : ~7-9% de reponses fausses restent, quel que soit
le seuil). Ce gate ajoute une verification AVANT de servir, avec deux mecanismes composables et
tous deux FAIL-SAFE :

1. CONSENSUS (frugal, zero dependance) : il regarde les k meilleurs golds. Si plusieurs candidats
   PROCHES en score se CONTREDISENT (reponses differentes), la question est ambigue ou mal couverte
   -> on s'abstient. C'est un desaccord INTERNE au corpus, mesurable sans aucun modele ni 2e canal.
2. VERIFIER (optionnel) : un callable (question, reponse) -> ancrage 0..1 (p.ex. un petit modele
   NLI sur CPU, branche plus tard). Sous le seuil -> abstention. Absent -> seul le consensus joue.

Fail-safe par construction : sans `match_topk` sur le reseau interne ET sans verifier, le gate est
un simple passe-plat (comportement inchange) -> il ne peut RIEN casser. Il ne fait jamais qu'OTER
des reponses douteuses ; il n'en invente aucune. Fidele a l'ADN : mieux vaut s'abstenir que servir
un fait faux avec aplomb.

Ancrage : reject-option (Chow 1970), desaccord de comite / query-by-committee (Seung 1992),
verification d'entailment generateur-verificateur (CRITIC ; MiniCheck 2024). Le consensus est 100%
deterministe et O(k).

    from cybnodes.networks import RecallNetwork, GroundingGate
    net = GroundingGate(RecallNetwork(pairs=PAIRS))     # consensus seul, zero dependance
    net.match("le sang c'est quoi")                     # -> None si des golds proches divergent
"""
from __future__ import annotations

import re
import unicodedata
from typing import Callable, Optional, Set

from ..network import Manifest, Network
from ..result import Result

# Un verifier juge l'ancrage d'une reponse a une question : (question, reponse) -> 0..1.
Verifier = Callable[[str, str], float]

_MIN_TOK = 2  # on ignore les tokens d'une lettre pour comparer le CONTENU des reponses


def _norm(s: str) -> str:
    t = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _content(s: str) -> Set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", _norm(s)) if len(w) > _MIN_TOK}


class GroundingGate(Network):
    """Enveloppe un reseau et VERIFIE sa reponse avant de la servir (consensus + verifier optionnel).

    Ne renvoie que ce que le reseau interne renvoie deja -- jamais une reponse nouvelle. En cas de
    doute (golds proches en desaccord, ou verifier sous le seuil), il s'abstient (None)."""

    name = "grounding"
    manifest = Manifest(
        answers="verifie l'ancrage d'une reponse recuperee (consensus des golds + verifier optionnel) avant de la servir",
        deterministic=True,
        needs_source=True,
        fallback="pass",
    )

    def __init__(self,
                 inner: Network,
                 verifier: Optional[Verifier] = None,
                 min_entailment: float = 0.5,
                 consensus: bool = True,
                 k: int = 4,
                 consensus_margin: float = 0.85,
                 answer_sim_thr: float = 0.4,
                 answer_clusters: Optional[dict] = None,
                 conflict_pairs: Optional[list] = None,
                 conflict_mode: str = "auto"):
        """inner : le reseau a proteger (idealement un RecallNetwork, qui expose match_topk).

        consensus       : active la detection de desaccord interne (rivaux proches qui divergent).
        k               : nombre de candidats examines pour le consensus.
        consensus_margin: un rival compte s'il est a >= margin * (score du meilleur). 0.85 = proche.
        answer_sim_thr  : deux reponses "divergent" si leur recouvrement de contenu < ce seuil (repli).
        answer_clusters : {reponse_normalisee: cluster_id} PRE-CALCULE hors-ligne par entailment
                          bidirectionnel (semantic entropy, Kuhn/Gal/Farquhar). Si fourni, la
                          decision de conflit se fait par comparaison de CLUSTER (semantique) au lieu
                          du recouvrement de tokens -> corrige le faux conflit "meme sens/mots
                          differents". Lookup O(1), zero modele a l'inference. None -> repli tokens.
        conflict_pairs  : paires [rep_a, rep_b] marquees CONTRADICTION hors-ligne (desaccord dur,
                          jamais fusionnable) -> conflit meme si les scores sont proches.
        verifier        : callable optionnel (question, reponse) -> 0..1 (NLI en ligne, non requis).
        min_entailment  : sous ce score du verifier -> abstention.
        """
        self.inner = inner
        self.verifier = verifier
        self.min_entailment = float(min_entailment)
        self.consensus = bool(consensus)
        self.k = int(k)
        self.consensus_margin = float(consensus_margin)
        self.answer_sim_thr = float(answer_sim_thr)
        self.clusters = answer_clusters
        self.conflicts = frozenset(
            frozenset((_norm(a), _norm(b))) for a, b in (conflict_pairs or []))
        # "auto" : cluster si artefact dispo, sinon token. "contradiction" : conflit UNIQUEMENT sur
        # une contradiction NLI averee (redondance/neutre servie). "cluster"/"token" : forcer un mode.
        self.conflict_mode = conflict_mode

    def _answer_sim(self, a: str, b: str) -> float:
        ta, tb = _content(a), _content(b)
        if not ta or not tb:
            return 1.0  # pas de contenu comparable -> on ne declenche pas de conflit
        return len(ta & tb) / min(len(ta), len(tb))  # coefficient de recouvrement

    def _cluster_of(self, ans: str):
        return self.clusters.get(_norm(ans)) if self.clusters else None

    def _hard_conflict(self, a: str, b: str) -> bool:
        return frozenset((_norm(a), _norm(b))) in self.conflicts

    def _rivals(self, topk):
        """Les candidats PROCHES en score du meilleur (rivaux credibles)."""
        best_score = topk[0][0]
        for score, ans, _src in topk[1:]:
            if score < best_score * self.consensus_margin:
                break  # trop loin en score -> plus de rival credible
            yield ans

    def _conflict(self, topk) -> bool:
        """Vrai si un rival proche du meilleur dit AUTRE CHOSE. Mode 'contradiction' : conflit
        UNIQUEMENT sur une contradiction NLI averee (le plus lenient, sert la redondance). Mode
        'cluster' : conflit si clusters differents (equivalence stricte). Mode 'token' : repli
        lexical. 'auto' : cluster si dispo, sinon token."""
        if len(topk) < 2 or topk[0][0] <= 0:
            return False
        best_ans = topk[0][1]
        mode = self.conflict_mode
        if mode == "auto":
            mode = "cluster" if (self.clusters and self._cluster_of(best_ans) is not None) else "token"
        if mode == "contradiction":
            # on ne s'abstient QUE si un rival proche CONTREDIT (NLI). Neutre/redondant -> on sert.
            for ans in self._rivals(topk):
                if self._hard_conflict(best_ans, ans):
                    return True
            return False
        if mode == "cluster" and self.clusters and self._cluster_of(best_ans) is not None:
            bc = self._cluster_of(best_ans)
            for ans in self._rivals(topk):
                rc = self._cluster_of(ans)
                if rc is None or rc != bc or self._hard_conflict(best_ans, ans):
                    return True                  # inconnu / cluster different / contradiction
            return False                         # tous les rivaux proches = MEME sens -> redondance
        # repli LEXICAL (comportement historique)
        for ans in self._rivals(topk):
            if self._answer_sim(best_ans, ans) < self.answer_sim_thr:
                return True
        return False

    def match(self, question: str) -> Optional[Result]:
        result = self.inner.match(question)
        if result is None:
            return None  # le reseau interne s'est deja abstenu
        # 1. consensus : si des golds proches en score se contredisent, on s'abstient.
        if self.consensus and hasattr(self.inner, "match_topk"):
            if self._conflict(self.inner.match_topk(question, k=self.k)):
                return None
        # 2. verifier optionnel (NLI plus tard). Un verifier qui plante ne bloque pas (fail-safe).
        if self.verifier is not None:
            try:
                score = float(self.verifier(question, result.text))
            except Exception:
                score = 1.0
            if score < self.min_entailment:
                return None
        return result

    def __repr__(self) -> str:  # pragma: no cover
        return "<GroundingGate sur %r verifier=%s>" % (self.inner, self.verifier is not None)
