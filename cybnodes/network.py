"""Network : la brique de capacite. On en branche autant qu'on veut, elles sont independantes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .result import Result


class Network(ABC):
    """Un reseau de capacite (calcul, savoir, web, code...).

    Contrat : `match(question)` renvoie un `Result` si le reseau SAIT repondre de maniere
    sure/verifiable, sinon `None` (et la main passe au reseau suivant, puis au modele).
    Un reseau est sans etat partage : on peut l'ajouter ou le retirer sans casser les autres.
    """

    name: str = "network"

    @abstractmethod
    def match(self, question: str) -> Optional[Result]:
        ...

    def __repr__(self) -> str:  # pragma: no cover
        return "<Network %s>" % self.name
