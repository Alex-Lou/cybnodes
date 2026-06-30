"""Routage SEMANTIQUE : router par le SENS, pas par mots-cles.

Le matching par regex rate les reformulations et synonymes ("les matous" n'a pas le mot
"chat"). Un SemanticNetwork plonge la question et la compare a des phrases-prototypes : la
SIMILARITE devient la `confidence`, et le `threshold` du Router fait le gating habituel.

CybNodes ne depend de RIEN : tu INJECTES l'embedder que tu veux. Ci-dessous, un embedder
JOUET (zero dep) pour que l'exemple tourne tel quel ; en prod, decommente le vrai.

    python examples/semantic_routing.py
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import CybNodes, HybridNetwork, Persona, SemanticNetwork
from cybnodes.networks import CalculNetwork, SavoirNetwork


# --- 1) L'EMBEDDER : model-agnostic, injecte. EN PROD, utilise un vrai modele : -------------
#
#   from sentence_transformers import SentenceTransformer
#   _m = SentenceTransformer("all-MiniLM-L6-v2")
#   embed = lambda text: _m.encode(text).tolist()
#
# ...ou les embeddings OpenAI, Ollama, etc. CybNodes s'en fiche : c'est un callable str->list.
#
# Pour que cet exemple tourne SANS rien installer, un embedder jouet (synonymes -> meme axe) :
_CONCEPT = {
    "chat": "felin", "chats": "felin", "felin": "felin", "felins": "felin",
    "matou": "felin", "matous": "felin", "minou": "felin", "minous": "felin",
    "mange": "nourriture", "manger": "nourriture", "bouffe": "nourriture", "miam": "nourriture",
    "meteo": "meteo", "temps": "meteo", "pluie": "meteo", "dehors": "meteo", "froid": "meteo",
}
_DIMS = sorted(set(_CONCEPT.values()))


def embed(text):
    deacc = "".join(c for c in unicodedata.normalize("NFD", (text or "").lower())
                    if unicodedata.category(c) != "Mn")
    v = [0.0] * len(_DIMS)
    for w in re.findall(r"[a-z]+", deacc):
        if w in _CONCEPT:
            v[_DIMS.index(_CONCEPT[w])] += 1.0
    return v


# --- 2) LES RESEAUX : un exact (calcul), un hybride (graphe + sens) -------------------------
GRAPH = [
    {"s": "chat", "r": "est_un", "o": "animal"},
    {"s": "chat", "r": "mange", "o": "des croquettes"},
]

savoir_hybride = HybridNetwork(
    SavoirNetwork(triples=GRAPH),                       # voie EXACTE : intention + entite au graphe
    SemanticNetwork(                                    # voie du SENS : rattrape synonymes/reformulations
        name="savoir-flou",
        utterances=["c'est quoi un chat", "parle-moi des chats", "les felins et leur nourriture"],
        embedder=embed,
        answer="Le chat est un petit felin ; il aime manger.",
        floor=0.35,
        kind="savoir",
    ),
    name="savoir",
)

cyb = CybNodes(
    conductor=lambda q, ctx: "[le modele repond librement : %r]" % q,
    networks=[CalculNetwork(), savoir_hybride],
    persona=Persona(name="N3", templates={"savoir": ["{value}"]}),
    threshold=0.0,   # mets 0.6 pour exiger plus de certitude des reseaux flous
)

if __name__ == "__main__":
    essais = [
        "combien font 7 x 8 ?",          # -> calcul exact
        "c'est quoi un chat ?",          # -> graphe EXACT (mot-cle + entite)
        "raconte-moi sur les matous",    # -> SENS (pas le mot 'chat', pas d'entite au graphe)
        "les minous, ca mange quoi ?",   # -> SENS (synonyme + concept nourriture)
        "quel temps fait-il dehors ?",   # -> hors-domaine : le MODELE reprend
    ]
    for q in essais:
        print("%-34s %s" % (q, cyb.ask(q)))
