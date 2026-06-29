"""Router evals + manifeste + evidence (v0.2).

Le routeur EST le produit : ce qui compte, c'est qu'il choisisse la bonne capacite, et que
la reponse finale reste DANS ce que la capacite a prouve. Ce fichier mesure exactement ca,
sur des categories franches : calcul simple, calcul cache dans une phrase, info recente,
fait connu du graphe, fait inconnu, conversation normale.

Lancement : python tests/test_router.py   (ou `pytest`). Self-contained.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import CybNodes, Network, Persona, Result, Weaver  # noqa: E402
from cybnodes.networks import CalculNetwork, SavoirNetwork, WebNetwork  # noqa: E402

GRAPH = [
    {"s": "chat", "r": "est_un", "o": "animal"},
    {"s": "chat", "r": "fait", "o": "miaou"},
    {"s": "soleil", "r": "est_un", "o": "etoile"},
]

# un faux web deterministe -> on teste le ROUTAGE sans reseau ni cle reelle
_FAKE_WEB = {"web": {"results": [
    {"title": "Mars", "description": "Actu <b>Mars</b> du jour.", "url": "http://ex/mars"},
]}}


def _cyb():
    return CybNodes(
        conductor=lambda q, ctx: "MODELE",
        networks=[
            CalculNetwork(),
            SavoirNetwork(triples=GRAPH),
            WebNetwork(api_key="FAKE", fetch=lambda q: _FAKE_WEB),
        ],
    )


# (question, capacite attendue OU None = le modele doit reprendre la main)
CASES = [
    ("combien font 7 x 8 ?",                              "calcul"),   # calcul simple
    ("si je prends 120 + 45 ca fait combien au total ?",  "calcul"),   # calcul cache dans une phrase
    ("quoi de neuf sur Mars en ce moment ?",              "web"),      # info recente
    ("c'est quoi un chat ?",                              "savoir"),   # fait connu du graphe
    ("c'est quoi un dragon ?",                             None),      # fait inconnu -> modele
    ("bonjour, comment ca va ?",                          None),       # conversation normale -> modele
    ("raconte-moi une petite histoire",                   None),       # intention savoir sans entite -> modele
]


def test_router_picks_the_right_skill():
    """Metrique : pour chaque cas, le routeur a-t-il choisi la bonne capacite (ou rendu la main) ?"""
    cyb = _cyb()
    score, lines = 0, []
    for question, expected in CASES:
        hit = cyb.route_only(question)
        got = hit.kind if hit is not None else None
        ok = got == expected
        score += ok
        lines.append("  [%s] %-45s -> %s (attendu %s)" % ("OK" if ok else "XX", question, got, expected))
    print("\n".join(lines))
    print("  router score : %d/%d" % (score, len(CASES)))
    assert score == len(CASES), "le routeur s'est trompe de capacite sur au moins un cas"


def test_answer_stays_inside_what_the_skill_proved():
    """La reponse finale d'une capacite ne doit pas inventer hors de ce qu'elle a prouve."""
    cyb = _cyb()
    # calcul : la valeur exacte, rien d'autre
    assert "63" in cyb.ask("100 - 37")
    # savoir : seulement des faits du graphe (pas de fait hors-graphe)
    ans = cyb.ask("c'est quoi un chat ?")
    assert "animal" in ans and "miaou" in ans and "dragon" not in ans


def test_skills_manifest_introspection():
    """Chaque reseau declare ce qu'il sait faire -> introspectable via skills()."""
    sk = {s["name"]: s for s in _cyb().skills()}
    assert set(sk) == {"calcul", "savoir", "web"}
    assert sk["calcul"]["deterministic"] is True and sk["calcul"]["needs_source"] is False
    assert sk["savoir"]["needs_source"] is True
    assert sk["web"]["deterministic"] is False and sk["web"]["needs_source"] is True
    assert all(s["answers"] for s in sk.values())          # chacun decrit sa capacite
    assert all(s["fallback"] == "pass" for s in sk.values())


def test_evidence_cite_off_by_default():
    """cite=False (defaut) : la reponse reste EXACTEMENT comme avant (zero regression)."""
    w = Weaver()
    r = SavoirNetwork(triples=GRAPH).match("c'est quoi un chat ?")
    assert w.weave(r) == r.text                              # rien d'ajoute


def test_evidence_cite_surfaces_source():
    """cite=True : la source (le node, l'URL) remonte dans la reponse -> fiable, pas juste charmant."""
    w = Weaver(cite=True)
    r = SavoirNetwork(triples=GRAPH).match("c'est quoi un chat ?")
    out = w.weave(r)
    assert "source :" in out and "chat" in out              # le node utilise est cite
    # et via un gabarit, {source} est placable finement
    wt = Weaver(Persona(templates={"savoir": ["{value} [{source}]"]}))
    assert "[graphe de connaissances : chat]" in wt.weave(r)


class _FuzzyNet(Network):
    """Reseau FLOU de test : matche toujours, mais avec une certitude GRADUEE (pour le seuil)."""
    name = "fuzzy"

    def __init__(self, conf):
        self._conf = conf

    def match(self, question):
        return Result(kind="fuzzy", text="FLOU", confidence=self._conf)


def test_threshold_default_zero_regression():
    """threshold=0.0 (defaut) : tout Result non-None gagne, exactement comme avant le seuil."""
    cyb = _cyb()  # calcul/savoir/web sont tous a confidence 1.0
    assert cyb.route_only("combien font 7 x 8 ?").kind == "calcul"
    assert cyb.route_only("c'est quoi un chat ?").kind == "savoir"
    assert cyb.route_only("bonjour, comment ca va ?") is None


def test_threshold_skips_low_confidence():
    """Un Result sous le seuil est ignore -> le modele reprend la main (anti-embourbement)."""
    # sans seuil : meme une confiance basse passe (comportement historique)
    cyb0 = CybNodes(conductor=lambda q, c: "MODELE", networks=[_FuzzyNet(0.4)])
    assert cyb0.route_only("x").kind == "fuzzy" and cyb0.ask("x") == "FLOU"
    # seuil 0.6 : 0.4 < 0.6 -> on passe la main au conducteur
    cyb1 = CybNodes(conductor=lambda q, c: "MODELE", networks=[_FuzzyNet(0.4)], threshold=0.6)
    assert cyb1.route_only("x") is None and cyb1.ask("x") == "MODELE"
    # confiance suffisante -> passe le seuil
    cyb2 = CybNodes(conductor=lambda q, c: "MODELE", networks=[_FuzzyNet(0.9)], threshold=0.6)
    assert cyb2.route_only("x").kind == "fuzzy"


def test_threshold_falls_through_to_next_network():
    """Un reseau sous le seuil ne BLOQUE pas : le routeur essaie le suivant (cascade)."""
    cyb = CybNodes(conductor=lambda q, c: "MODELE",
                   networks=[_FuzzyNet(0.3), _FuzzyNet(0.95)], threshold=0.6)
    hit = cyb.route_only("x")
    assert hit is not None and abs(hit.confidence - 0.95) < 1e-9


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK  ", t.__name__)
    print("--- %d/%d tests passes ---" % (len(tests), len(tests)))
