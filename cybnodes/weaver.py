"""Weaver (le Tisseur) : reprend le Result brut d'un reseau et le redit dans la VOIX de la persona.

C'est ce qui garde l'ame du conducteur quand c'est un outil (et pas le modele) qui repond.
La persona porte des gabarits par `kind` ; `{value}` = la reponse brute, `{source}` = la
tracabilite, plus tous les champs de `result.data`. Sans gabarit pour ce kind, on renvoie
`result.text` tel quel.

`cite=True` fait remonter la SOURCE dans la reponse finale (le node du graphe, l'URL, le
calcul exact) : c'est ce qui rend un petit modele *fiable* et pas juste *charmant*. Defaut
`False` -> la reponse reste exactement comme avant (la source vit dans `result.source` et
reste disponible via `{source}` dans un gabarit pour un placement fin).
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


# Phrases d'incertitude par defaut, servies quand la confiance est SOUS le seuil
# (selective prediction / abstention douce, Chow 1970) : la persona ADMET le doute au lieu
# d'affirmer avec aplomb. Surchargeables via persona.templates["_hedge"] ou Weaver(hedges=[...]).
_DEFAULT_HEDGES = [
    "Je ne suis pas tout a fait sure, mais je crois que... {value}",
    "Hmm, a verifier, mais il me semble que... {value}",
    "Je dirais... {value} (a confirmer !)",
]


class Weaver:
    def __init__(self, persona: Optional[Persona] = None, cite: bool = False,
                 hedge_below: float = 0.0, hedges: Optional[List[str]] = None):
        self.persona = persona or Persona()
        self.cite = cite
        self.hedge_below = float(hedge_below)   # 0.0 -> jamais de nuance (comportement historique)
        self.hedges = list(hedges) if hedges is not None else None

    def weave(self, result: Result) -> str:
        text = self._render(result)
        # NUANCE par confiance : sous le seuil, on admet le doute plutot que d'asséner.
        if self.hedge_below > 0.0 and result.confidence < self.hedge_below:
            text = self._hedge(result, text)
        if self.cite and result.source and result.source not in text:
            text = "%s (source : %s)" % (text, result.source)
        return text

    def _hedge(self, result: Result, text: str) -> str:
        opts = self.persona.template_for("_hedge") or self.hedges or _DEFAULT_HEDGES
        tpl = opts[sum(ord(c) for c in str(result.text)) % len(opts)]
        try:
            return tpl.format(value=text, source=result.source or "", **result.data)
        except (KeyError, IndexError, ValueError):
            return tpl.replace("{value}", text)

    def _render(self, result: Result) -> str:
        templates = self.persona.template_for(result.kind)
        if not templates:
            return result.text
        # choix deterministe (pas de hasard -> testable/reproductible) base sur le contenu
        seed = str(result.data.get("expr") or result.data.get("entity") or result.text)
        tpl = templates[sum(ord(c) for c in seed) % len(templates)]
        # {value} = TOUJOURS la reponse brute lisible ; {source} = la tracabilite. Reserves,
        # mis APRES les data pour qu'une cle data homonyme ne les ecrase pas.
        fields = dict(result.data)
        fields["value"] = result.text
        fields["source"] = result.source or ""
        try:
            return tpl.format(**fields)
        except (KeyError, IndexError, ValueError):
            return tpl.replace("{value}", result.text)
