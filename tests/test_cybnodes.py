"""Tests CybNodes : calcul, savoir (GraphRAG), tissage, memoire, fallback conducteur.

Lancement : depuis le dossier cybnodes/  ->  python tests/test_cybnodes.py
(ou `pytest` si installe). Self-contained : ajoute le package au path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import CybNodes, Memory, Persona  # noqa: E402
from cybnodes.networks import CalculNetwork, SavoirNetwork, WebNetwork  # noqa: E402

GRAPH = [
    {"s": "chat", "r": "est_un", "o": "animal"},
    {"s": "chat", "r": "fait", "o": "miaou"},
    {"s": "chat", "r": "mange", "o": "des croquettes"},
    {"s": "soleil", "r": "est_un", "o": "etoile"},
]


def test_calcul_exact():
    net = CalculNetwork()
    assert net.match("combien font 7 x 8 ?").data["value"] == 56
    assert net.match("100 - 37").data["value"] == 63
    assert net.match("245 multiplie par 6").data["value"] == 1470
    assert net.match("10 divise par 4").data["value"] == 2.5
    assert net.match("2 puissance 10").data["value"] == 1024   # 'puissance' repare
    assert net.match("j'ai 30 ans") is None                    # un seul nombre -> pas un calcul
    assert net.match("j'aime les chats") is None


def test_savoir_graphrag():
    net = SavoirNetwork(triples=GRAPH)
    r = net.match("c'est quoi un chat ?")
    assert r is not None and r.data["entity"] == "chat"
    assert "animal" in r.text and "miaou" in r.text
    assert net.match("j'ai vu un chat") is None        # pas d'intention de savoir -> None
    assert net.match("c'est quoi un dragon ?") is None  # entite inconnue -> None


def test_routing_and_voice():
    cyb = CybNodes(
        conductor=lambda q, ctx: "MODELE: " + q,
        networks=[CalculNetwork(), SavoirNetwork(triples=GRAPH)],
        persona=Persona(templates={"calcul": ["Hop, {value} !"]}),
    )
    assert cyb.ask("3 + 4") == "Hop, 3 + 4 = 7 !"          # calcul -> tisse
    assert "animal" in cyb.ask("c'est quoi un chat ?")     # savoir -> brut (pas de gabarit)
    assert cyb.ask("bonjour ca va ?") == "MODELE: bonjour ca va ?"  # fallback conducteur


def test_memory_capture():
    def capt(msg):
        return ["L'utilisateur s'appelle Marie"] if "je suis marie" in msg.lower() else []

    captured = {}
    cyb = CybNodes(
        conductor=lambda q, ctx: "ctx=%s" % ctx,
        memory=Memory(capturers=[capt]),
    )
    cyb.ask("Je suis Marie")
    assert "Marie" in cyb.ask("tu te souviens ?")   # le fait capte est injecte en contexte


def test_web_search():
    fake = {"web": {"results": [
        {"title": "Mars", "description": "La planete <b>Mars</b> est rouge.", "url": "http://ex/mars"},
    ]}}
    net = WebNetwork(api_key="FAKE", fetch=lambda q: fake)
    r = net.match("cherche des infos sur Mars")
    assert r is not None and "Mars est rouge" in r.text and r.source == "http://ex/mars"
    assert net.match("je t'aime bien") is None          # pas d'intention de recherche -> None
    # sans cle : degrade proprement (le modele repondra)
    assert WebNetwork(api_key=None, fetch=lambda q: fake).match("cherche Mars") is None


def test_network_failure_is_safe():
    class Boom(CalculNetwork):
        def match(self, q):
            raise RuntimeError("boom")

    cyb = CybNodes(conductor=lambda q, ctx: "ok", networks=[Boom()])
    assert cyb.ask("salut") == "ok"   # un reseau qui plante n'ecroule pas le circuit


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK  ", t.__name__)
    print("--- %d/%d tests passes ---" % (len(tests), len(tests)))
