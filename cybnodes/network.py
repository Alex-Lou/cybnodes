"""Network : la brique de capacite. On en branche autant qu'on veut, elles sont independantes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .result import Result


@dataclass(frozen=True)
class Manifest:
    """Ce qu'un reseau DECLARE savoir faire : la fiche d'identite de la capacite.

    Sert la documentation, l'introspection (`CybNodes.skills()`) et, plus tard, un routeur
    plus malin (qui pourra ordonner/filtrer selon `deterministic` ou `needs_source`).
    Purement declaratif : ca ne change PAS le comportement de `match()`.

    - answers       : ce que le reseau sait repondre (une ligne lisible).
    - deterministic : la reponse est-elle exacte/reproductible (calcul) ou variable (web) ?
    - needs_source  : la reponse devrait-elle porter une source verifiable (savoir, web) ?
    - fallback      : que faire quand le reseau ne sait pas. "pass" = rendre la main (defaut).
    """
    answers: str
    deterministic: bool = True
    needs_source: bool = False
    fallback: str = "pass"


class Network(ABC):
    """Un reseau de capacite (calcul, savoir, web, code...).

    Contrat : `match(question)` renvoie un `Result` si le reseau SAIT repondre de maniere
    sure/verifiable, sinon `None` (et la main passe au reseau suivant, puis au modele).
    Un reseau est sans etat partage : on peut l'ajouter ou le retirer sans casser les autres.

    `manifest` (optionnel) declare ce que le reseau sait faire -> introspection et docs.
    """

    name: str = "network"
    manifest: Optional[Manifest] = None

    @abstractmethod
    def match(self, question: str) -> Optional[Result]:
        ...

    def __repr__(self) -> str:  # pragma: no cover
        return "<Network %s>" % self.name
