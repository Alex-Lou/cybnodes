"""CybNodes : un petit conducteur a personnalite entoure de reseaux de nodes par capacite.

Principe (framework de CybWu) : on n'alourdit pas le cerveau par force brute ; on l'entoure
de circuits structures et verifiables. Un petit modele peut alors alimenter un systeme
qui "pese" bien plus lourd.

    from cybnodes import CybNodes, Persona
    from cybnodes.networks import CalculNetwork, SavoirNetwork

    cyb = CybNodes(
        conductor=mon_llm,                       # callable(question, context) -> str
        networks=[CalculNetwork(), SavoirNetwork(graph_path="graphe.json")],
        persona=Persona(name="N3", templates={"calcul": ["Hop, {value} !"]}),
    )
    cyb.ask("combien font 7 x 8 ?")   # -> reponse EXACTE, tissee dans la voix
"""
from .core import CybNodes
from .memory import Memory
from .network import Manifest, Network
from .result import Result
from .router import Router
from .semantic import Embedder, HybridNetwork, SemanticNetwork, cosine
from .weaver import Persona, Weaver

__all__ = [
    "CybNodes", "Network", "Manifest", "Result", "Router", "Weaver", "Persona", "Memory",
    "SemanticNetwork", "HybridNetwork", "cosine", "Embedder",
]
__version__ = "0.5.0"
