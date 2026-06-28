"""Router : lit l'intention via les reseaux, choisit le premier qui prend la main.

Regles d'abord (fiable), modele ensuite. Un reseau qui leve une exception est ignore
(fail-safe) : il ne doit jamais faire tomber tout le circuit.
"""
from __future__ import annotations

from typing import List, Optional

from .network import Network
from .result import Result


class Router:
    def __init__(self, networks: Optional[List[Network]] = None):
        self.networks: List[Network] = list(networks or [])

    def add(self, network: Network) -> "Router":
        self.networks.append(network)
        return self

    def route(self, question: str) -> Optional[Result]:
        for net in self.networks:
            try:
                result = net.match(question)
            except Exception:
                result = None  # un reseau fragile ne casse jamais le circuit
            if result is not None:
                return result
        return None
