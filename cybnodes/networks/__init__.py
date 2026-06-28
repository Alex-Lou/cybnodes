"""Reseaux de capacite livres avec CybNodes. Ecris les tiens en heritant de `cybnodes.Network`."""
from .calcul import CalculNetwork
from .savoir import SavoirNetwork
from .web import WebNetwork

__all__ = ["CalculNetwork", "SavoirNetwork", "WebNetwork"]
