"""Tests CybNodes : calcul, savoir (GraphRAG), tissage, memoire, fallback conducteur.

Lancement : depuis le dossier cybnodes/  ->  python tests/test_cybnodes.py
(ou `pytest` si installe). Self-contained : ajoute le package au path.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import CybNodes, Memory, Persona  # noqa: E402
from cybnodes.networks import CalculNetwork, MathNetwork, SavoirNetwork, WebNetwork  # noqa: E402

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


def test_calcul_gating_and_safety():
    net = CalculNetwork()
    # gating d'intention : pas de calcul sur une phrase emotionnelle ni une date
    assert net.match("3+3 tu es belle") is None
    assert net.match("on se voit le 12/05/2024") is None
    # mais un vrai calcul passe (isole ou avec intention)
    assert net.match("3+3").data["value"] == 6
    assert net.match("combien font 12 / 4 ?").data["value"] == 3
    # securite : pas de DoS exponentiel -> None (le modele reprend la main)
    assert net.match("9**9**9") is None
    assert net.match("2 ** 100000") is None
    # division par zero : honnete, pas de None silencieux qui laisserait halluciner
    r = net.match("5 / 0")
    assert r is not None and "zero" in r.text.lower()


def test_web_cache():
    calls = {"n": 0}

    def fake(q):
        calls["n"] += 1
        return {"web": {"results": [{"title": "X", "description": "desc", "url": "http://x"}]}}

    net = WebNetwork(api_key="FAKE", fetch=fake)
    net.match("cherche X")
    net.match("cherche X")   # 2e fois identique -> cache, aucun 2e appel (= pas de $)
    assert calls["n"] == 1


def test_maths_network():
    net = MathNetwork()
    if net.match("derivee de x^2") is None:
        print("   (sympy non installe : MathNetwork se tait proprement, test saute)")
        return
    def res(q):
        r = net.match(q)
        assert r is not None, "pas de match: " + q
        return r.data["result"].replace(" ", "")
    assert res("calcule la derivee de x^2") == "2*x"
    assert res("integrale de x^2") == "x**3/3"
    assert res("integrale de x^2 de 0 a 1") == "1/3"
    sols = set(net.match("resous x^2 - 5x + 6 = 0").data["solutions"])
    assert sols == {"2", "3"}, sols
    assert res("simplifie (x^2-1)/(x-1)") == "x+1"
    assert net.match("factorise x^2 - 4").data["result"].replace(" ", "") in ("(x-2)*(x+2)", "(x+2)*(x-2)")
    assert res("developpe (x+1)^2") == "x**2+2*x+1"
    assert res("limite de sin(x)/x quand x tend vers 0") == "1"
    # ne vole PAS l'arithmetique de base (-> CalculNetwork) ni une phrase quelconque
    assert net.match("combien font 2+2") is None
    assert net.match("j'aime les maths") is None


def test_savoir_confidence():
    net = SavoirNetwork(triples=GRAPH)
    rich = net.match("c'est quoi un chat ?")      # 3 faits dans GRAPH
    thin = net.match("c'est quoi le soleil ?")     # 1 seul fait
    # les DEUX repondent (seuil 0 par defaut, rien ne change pour le routage de base)
    assert rich is not None and thin is not None
    # mais un sujet riche/specifique inspire plus de confiance qu'un fait unique
    assert rich.confidence > thin.confidence
    assert 0.0 < thin.confidence <= 1.0 and rich.confidence <= 1.0


def test_web_confidence():
    fake = {"web": {"results": [{"title": "X", "description": "un fait reel", "url": "http://x"}]}}
    net = WebNetwork(api_key="FAKE", fetch=lambda q: fake)
    strong = net.match("cherche des infos sur X")  # intention forte
    weak = net.match("X aujourd'hui")               # intention faible (signal ambigu)
    assert strong is not None and weak is not None  # les deux passent a seuil 0
    assert strong.confidence > weak.confidence       # l'intention forte inspire plus confiance


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK  ", t.__name__)
    print("--- %d/%d tests passes ---" % (len(tests), len(tests)))
