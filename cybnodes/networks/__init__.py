"""Reseaux de capacite livres avec CybNodes. Ecris les tiens en heritant de `cybnodes.Network`."""
from .calcul import CalculNetwork
from .grounding import GroundingGate
from .maths import MathNetwork
from .recall import RecallNetwork
from .savoir import SavoirNetwork
from .web import WebNetwork

__all__ = ["CalculNetwork", "GroundingGate", "MathNetwork", "RecallNetwork", "SavoirNetwork", "WebNetwork"]
