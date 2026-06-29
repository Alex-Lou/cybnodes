"""Result : ce qu'un reseau renvoie quand il prend la main."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Result:
    """Resultat brut d'un reseau, avant tissage.

    - kind     : type de reseau ("calcul", "savoir", "web"...) -> choisit le gabarit du Tisseur.
    - text     : reponse lisible (fallback si la persona n'a pas de gabarit pour ce kind).
    - data     : donnees structurees (champs nommes reutilisables par les gabarits).
    - source   : tracabilite -> rend la reponse VERIFIABLE (calcul exact, node du graphe, URL...).
    - confidence : 0..1, certitude du reseau. Le routeur ne retient le Result que si
                   confidence >= son threshold (defaut 0.0 -> tout passe). Les reseaux flous
                   (savoir, web) la graduent ; les deterministes restent a 1.0 (ou None).
    """
    kind: str
    text: str
    data: dict = field(default_factory=dict)
    source: Optional[str] = None
    confidence: float = 1.0
