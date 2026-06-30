"""Cache SEMANTIQUE optionnel et CALIBRE : repond a une question deja vue (ou tres proche)
sans rejouer reseaux/web/modele. Gros gain perf/cout, surtout sur un hote lent (CPU).

DOCTRINE + SINCERITE : un faux hit = servir une reponse proche-mais-FAUSSE = mentir. Donc :
  * seuil CONSERVATEUR par defaut (0.95) -- la perf ne coute jamais la sincerite ;
  * `calibrate()` derive le seuil de TES donnees (la "courbe" validee : balayer le seuil sur
    des paires etiquetees et prendre le plus bas qui tient un faux-hit-rate cible) ;
  * on ne cache JAMAIS l'incertitude (un Result de confiance basse n'est pas fige).

ZERO dependance : l'embedder est INJECTE (model-agnostic). Deux etages :
  - EXACT     : meme question normalisee -> reponse identique. Sans perte, zero risque.
  - SEMANTIQUE: question proche (cosinus >= threshold). Conservateur, calibrable PAR cache (route).

Etudes : le seuil est un compromis precision/rappel a CALIBRER PAR ROUTE, jamais une constante ;
0.7 (defaut GPTCache) est trop bas ; conservateur ~0.95-0.97 (faux-positifs <0.5%). Valider le
seuil sur des donnees representatives (pas via PR-AUC, qui ne mesure que le classement).
"""
from __future__ import annotations

import re
import time
import unicodedata
from typing import List, Optional, Sequence, Tuple

from .result import Result
from .semantic import Embedder, cosine


def _norm(s: str) -> str:
    """Cle EXACTE : minuscule, sans accents, ponctuation -> espace, espaces ecrases."""
    t = unicodedata.normalize("NFD", (s or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


class SemanticCache:
    """Cache a deux etages. `embedder` optionnel : sans lui, seul l'etage EXACT fonctionne
    (deja utile et 100% sur). `threshold` conservateur par defaut ; cale-le avec `calibrate()`.
    `ttl` (secondes) expire les entrees (mets-le court pour le web/temps-sensible). `min_confidence`
    sous lequel on ne cache PAS (ne pas figer l'incertitude).
    """

    def __init__(self, embedder: Optional[Embedder] = None, threshold: float = 0.95,
                 ttl: Optional[float] = None, max_size: int = 2000, min_confidence: float = 0.5):
        self._embedder = embedder
        self.threshold = threshold
        self.ttl = ttl
        self.max_size = max_size
        self.min_confidence = min_confidence
        self._exact: dict = {}                 # cle_norm -> (Result, ts)
        self._sem: List[Tuple[Sequence[float], str, Result, float]] = []  # (vec, q, Result, ts)
        self.hits = 0
        self.misses = 0

    def _fresh(self, ts: float, now: float) -> bool:
        return self.ttl is None or (now - ts) <= self.ttl

    def get(self, question: str, now: Optional[float] = None) -> Optional[Result]:
        now = time.time() if now is None else now
        # 1) etage EXACT : sans perte, zero risque
        hit = self._exact.get(_norm(question))
        if hit is not None and self._fresh(hit[1], now):
            self.hits += 1
            return hit[0]
        # 2) etage SEMANTIQUE : seulement au-dessus du seuil calibre
        if self._embedder is not None and self._sem:
            q = self._embedder(question or "")
            best, best_sim = None, 0.0
            for vec, _, res, ts in self._sem:
                if not self._fresh(ts, now):
                    continue
                s = cosine(q, vec)
                if s > best_sim:
                    best, best_sim = res, s
            if best is not None and best_sim >= self.threshold:
                self.hits += 1
                return best
        self.misses += 1
        return None

    def put(self, question: str, result: Optional[Result], now: Optional[float] = None) -> None:
        # ne fige JAMAIS l'incertitude (protege la sincerite)
        if result is None or getattr(result, "confidence", 1.0) < self.min_confidence:
            return
        now = time.time() if now is None else now
        self._exact[_norm(question)] = (result, now)
        if self._embedder is not None:
            self._sem.append((self._embedder(question or ""), question, result, now))
        self._evict()

    def _evict(self) -> None:
        while len(self._sem) > self.max_size:
            self._sem.pop(0)                    # FIFO simple
        if len(self._exact) > self.max_size:
            for k in list(self._exact)[: len(self._exact) - self.max_size]:
                del self._exact[k]

    def calibrate(self, positives: Sequence[Tuple[str, str]],
                  negatives: Sequence[Tuple[str, str]],
                  target_false_hit_rate: float = 0.01) -> Tuple[float, List[dict]]:
        """LA COURBE (methode validee). `positives` = paires qui DOIVENT partager une reponse ;
        `negatives` = paires qui ne doivent PAS. On balaie le seuil de 0 a 1 et on choisit le
        seuil le PLUS BAS (donc meilleur hit-rate) dont le faux-hit-rate reste <= la cible.
        Pose `self.threshold` et renvoie (seuil_choisi, courbe). La courbe est une liste de
        {threshold, hit_rate, false_hit_rate} -> tracable / inspectable.
        """
        if self._embedder is None:
            raise ValueError("calibrate() a besoin d'un embedder injecte")
        pos = [cosine(self._embedder(a), self._embedder(b)) for a, b in positives]
        neg = [cosine(self._embedder(a), self._embedder(b)) for a, b in negatives]
        curve: List[dict] = []
        for i in range(101):
            t = i / 100.0
            hit = (sum(1 for s in pos if s >= t) / len(pos)) if pos else 0.0
            fhr = (sum(1 for s in neg if s >= t) / len(neg)) if neg else 0.0
            curve.append({"threshold": round(t, 2),
                          "hit_rate": round(hit, 3),
                          "false_hit_rate": round(fhr, 3)})
        admissible = [c["threshold"] for c in curve if c["false_hit_rate"] <= target_false_hit_rate]
        self.threshold = min(admissible) if admissible else 1.0
        return self.threshold, curve

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": round(self.hits / total, 3) if total else 0.0,
                "threshold": self.threshold, "size_exact": len(self._exact), "size_sem": len(self._sem)}
