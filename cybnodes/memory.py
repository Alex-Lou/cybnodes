"""Memory : capte des faits SURS sur l'utilisateur et les rappelle.

Backend pluggable : par defaut en RAM (un dict). Passe n'importe quel objet dict-like
PERSISTANT (Modal Dict, Redis, sqlite-dict...) pour survivre aux redemarrages.
Les "capturers" sont des callables `(message) -> list[str]` : a toi de fournir des
patterns SURS (zero pollution). On n'invente jamais un fait, on ne fait que capter.
"""
from __future__ import annotations

from typing import Callable, List, Optional


class Memory:
    def __init__(self, store: Optional[dict] = None,
                 capturers: Optional[List[Callable[[str], List[str]]]] = None,
                 max_facts: int = 40):
        self.store = store if store is not None else {}
        self.capturers: List[Callable[[str], List[str]]] = list(capturers or [])
        self.max_facts = max_facts

    def facts(self) -> List[str]:
        return list(self.store.get("facts", []))

    def add_capturer(self, capturer: Callable[[str], List[str]]) -> "Memory":
        self.capturers.append(capturer)
        return self

    def capture(self, message: str) -> List[str]:
        facts = self.facts()
        for capturer in self.capturers:
            try:
                found = capturer(message) or []
            except Exception:
                found = []
            for fact in found:
                if fact and fact not in facts:
                    facts.append(fact)
        facts = facts[-self.max_facts:]
        self.store["facts"] = facts
        return facts

    def recall(self, question: str = "") -> List[str]:
        return self.facts()
