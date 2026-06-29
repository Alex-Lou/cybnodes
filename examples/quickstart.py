"""Exemple minimal et runnable : `python examples/quickstart.py`

Montre les 3 chemins :
  - une question de CALCUL  -> réseau calcul (exact, tissé dans la voix)
  - une question de SAVOIR  -> GraphRAG sur un petit graphe
  - autre chose             -> aucun réseau ne répond -> le conducteur (ton modèle)
"""
from cybnodes import CybNodes, Persona, Weaver
from cybnodes.networks import CalculNetwork, SavoirNetwork

# Un petit graphe de connaissances (en vrai : charge un fichier via graph_path=...)
GRAPHE = [
    {"s": "chat", "r": "est_un", "o": "animal"},
    {"s": "chat", "r": "fait", "o": "miaou"},
    {"s": "chat", "r": "mange", "o": "des croquettes"},
]


def mon_modele(question, context):
    # Ici, branche ton vrai LLM (ollama, API, modèle local...).
    # Pour la démo, on renvoie juste un texte témoin.
    return "(ton modèle répondrait ici, avec sa voix)"


# cite=True -> la source (calcul exact, node du graphe, URL) remonte dans la réponse.
cyb = CybNodes(
    conductor=mon_modele,
    networks=[CalculNetwork(), SavoirNetwork(triples=GRAPHE)],
    weaver=Weaver(Persona(name="Aria", templates={
        "calcul": ["Voilà : {value} ✦", "{value}, et c'est exact !"],
        "savoir": ["{value}"],
    }), cite=True),
)

if __name__ == "__main__":
    for question in [
        "combien font 47 x 38 ?",
        "2 puissance 10",
        "c'est quoi un chat ?",
        "raconte-moi une histoire",
    ]:
        print(f"\nQ: {question}")
        print(f"A: {cyb.ask(question)}")

    # Introspection : ce que chaque réseau déclare savoir faire.
    print("\nCapacités branchées :")
    for s in cyb.skills():
        print(f"  - {s['name']}: {s['answers']} (déterministe={s['deterministic']}, source={s['needs_source']})")
