"""Routage SEMANTIQUE optionnel : router par le SENS, pas seulement par mots-cles.

Fidele a la doctrine du framework :
  * ZERO dependance dans le coeur -- l'`embedder` (texte -> vecteur) est INJECTE. Tu branches
    celui que tu veux (sentence-transformers, OpenAI, Ollama, un modele maison...) ; CybNodes
    ne depend de RIEN et reste model-agnostic.
  * La SIMILARITE devient la `confidence` -- donc le `threshold` du Router (depuis 0.4.0) fait
    le gating "decline-when-uncertain" SANS aucun changement au routeur. Sous le `floor`, le
    reseau rend la main (None), exactement comme un reseau deterministe hors de son domaine.
  * HYBRIDE : on melange librement, dans le MEME Router, des reseaux EXACTS (regex, confidence
    1.0) et SEMANTIQUES (confidence = similarite graduee). `HybridNetwork` combine les deux pour
    UNE capacite : voie exacte d'abord, sens en repli.

Pourquoi : le matching par regex/mots-cles rate les reformulations, synonymes et fautes
("les matous, ca mange quoi ?" n'a pas le mot "chat"). Le sens, lui, les rattrape.
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence

from .network import Manifest, Network
from .result import Result

# Un embedder : texte -> vecteur de flottants. N'IMPORTE lequel. Injecte par l'utilisateur.
Embedder = Callable[[str], Sequence[float]]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Similarite cosinus, pure Python (zero dependance).

    Renvoie 0.0 si l'un des vecteurs est vide, nul, de taille differente, ou porte des valeurs
    non numeriques / non finies (NaN, Inf). Jamais d'exception : un embedder fragile ne doit
    pas casser le routage.
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = na = nb = 0.0
    try:
        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y
    except TypeError:
        return 0.0  # composante non numerique -> on decline, on ne plante pas
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    if not (math.isfinite(dot) and math.isfinite(na) and math.isfinite(nb)):
        return 0.0  # NaN/Inf dans l'embedding -> 0.0 plutot que propager le poison
    return dot / math.sqrt(na * nb)


class SemanticNetwork(Network):
    """Un reseau qui matche PAR LE SENS.

    Tu lui donnes :
      - `utterances` : des phrases-exemples qui devraient le declencher (les prototypes),
      - `embedder`   : un callable texte -> vecteur (model-agnostic, injecte),
      - `responder`  : un callable question -> Result (calcule la vraie reponse) OU `answer` fixe,
      - `floor`      : la similarite minimale ; en-dessous, le reseau DECLINE (renvoie None).

    `match()` plonge la question, prend la similarite cosinus MAX aux prototypes -> c'est la
    `confidence` (graduee). Le Router la gate ensuite via son `threshold`. Les prototypes sont
    plonges UNE fois (au __init__), pas a chaque requete.
    """

    def __init__(
        self,
        name: str,
        utterances: Sequence[str],
        embedder: Embedder,
        responder: Optional[Callable[[str], Optional[Result]]] = None,
        answer: Optional[str] = None,
        floor: float = 0.35,
        kind: str = "semantic",
        manifest: Optional[Manifest] = None,
    ):
        if not utterances:
            raise ValueError("SemanticNetwork a besoin d'au moins une utterance-prototype")
        self.name = name
        self._embedder = embedder
        self._responder = responder
        self._answer = answer
        self._floor = floor
        self._kind = kind
        if manifest is not None:
            self.manifest = manifest
        # plonge les prototypes UNE fois -> match() ne paie que l'embedding de la question
        self._protos: List[Sequence[float]] = [embedder(u) for u in utterances]

    def similarity(self, question: str) -> float:
        """Similarite max de la question aux prototypes (0..1 pour des embeddings normalises)."""
        q = self._embedder(question or "")
        return max((cosine(q, p) for p in self._protos), default=0.0)

    def match(self, question: str) -> Optional[Result]:
        score = self.similarity(question)
        if score < self._floor:
            return None  # pas mon sens -> je decline, la main passe (anti-embourbement)
        if self._responder is not None:
            res = self._responder(question)
            if res is None:
                return None
            # certitude finale = MIN(certitude du routage, certitude de la reponse)
            res.confidence = round(min(res.confidence, score), 3)
            return res
        return Result(
            kind=self._kind,
            text=self._answer or "",
            data={"score": round(score, 3)},
            source="routage semantique",
            confidence=round(score, 3),
        )


class HybridNetwork(Network):
    """HYBRIDE pour UNE capacite : essaie d'abord la voie EXACTE (un reseau regex/deterministe,
    confidence telle quelle -- souvent 1.0), sinon bascule sur le SENS (un SemanticNetwork,
    confidence graduee). La precision du mot-cle quand il matche, la robustesse du sens sinon.

        savoir = HybridNetwork(SavoirNetwork(graph_path="g.json"),
                               SemanticNetwork("savoir-flou", utterances=[...], embedder=emb))
    """

    def __init__(self, exact: Network, semantic: SemanticNetwork, name: Optional[str] = None):
        self.name = name or getattr(exact, "name", "hybride")
        self.manifest = getattr(exact, "manifest", None)
        self._exact = exact
        self._semantic = semantic

    def match(self, question: str) -> Optional[Result]:
        res = self._exact.match(question)
        if res is not None:
            return res  # voie exacte (rapide, deterministe)
        return self._semantic.match(question)  # repli sur le sens
