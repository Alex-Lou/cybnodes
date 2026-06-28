"""Weaver (le Tisseur) : reprend le Result brut d'un reseau et le redit dans la VOIX de la persona.

C'est ce qui garde l'ame du conducteur quand c'est un outil (et pas le modele) qui repond.
La persona porte des gabarits par `kind` ; `{value}` = la reponse brute, plus tous les
champs de `result.data`. Sans gabarit pour ce kind, on renvoie `result.text` tel quel.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .result import Result


@dataclass
class Persona:
    name: str = "CybNodes"
    templates: Dict[str, List[str]] = field(default_factory=dict)

    def template_for(self, kind: str) -> Optional[List[str]]:
        return self.templates.get(kind)


class Weaver:
    def __init__(self, persona: Optional[Persona] = None):
        self.persona = persona or Persona()

    def weave(self, result: Result) -> str:
        templates = self.persona.template_for(result.kind)
        if not templates:
            return result.text
        # choix deterministe (pas de hasard -> testable/reproductible) base sur le contenu
        seed = str(result.data.get("expr") or result.data.get("entity") or result.text)
        tpl = templates[sum(ord(c) for c in seed) % len(templates)]
        # {value} = TOUJOURS la reponse brute lisible (reserve, mis apres les data
        # pour qu'une cle data nommee "value" ne l'ecrase pas). {expr}, {entity}... = data.
        fields = dict(result.data)
        fields["value"] = result.text
        try:
            return tpl.format(**fields)
        except (KeyError, IndexError, ValueError):
            return tpl.replace("{value}", result.text)
