"""CybNodes : le conducteur a personnalite + ses reseaux.

    ask(question) :
      1. (option) capte les faits surs -> Memoire
      2. ROUTEUR : un reseau prend-il la main ? -> TISSEUR (reponse exacte, dans la voix)
      3. sinon -> CONDUCTEUR (TON modele) avec le contexte memoire

Model-agnostic : tu apportes ton LLM via `conductor=callable(question, context) -> str`.
Le squelette (routeur/reseaux/tisseur/memoire) se transfere tel quel d'un modele a l'autre.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from .memory import Memory
from .network import Network
from .result import Result
from .router import Router
from .weaver import Persona, Weaver


class CybNodes:
    def __init__(self,
                 conductor: Optional[Callable[[str, Optional[str]], str]] = None,
                 networks: Optional[List[Network]] = None,
                 persona: Optional[Persona] = None,
                 weaver: Optional[Weaver] = None,
                 memory: Optional[Memory] = None):
        self.router = Router(networks)
        self.weaver = weaver or Weaver(persona)
        self.memory = memory
        self.conductor = conductor

    def add_network(self, network: Network) -> "CybNodes":
        self.router.add(network)
        return self

    def route_only(self, question: str) -> Optional[Result]:
        """Debug/test : le Result brut du routeur, sans tissage ni modele."""
        return self.router.route((question or "").strip())

    def ask(self, question: str, context: Optional[str] = None) -> Optional[str]:
        q = (question or "").strip()
        if not q:
            return None
        if self.memory:
            self.memory.capture(q)
        hit = self.router.route(q)
        if hit is not None:
            return self.weaver.weave(hit)
        if self.conductor is not None:
            if context is None and self.memory:
                facts = self.memory.recall(q)
                context = " ".join(facts) if facts else None
            return self.conductor(q, context)
        return None
