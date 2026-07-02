"""Routage SEMANTIQUE : prouve que le routage PAR LE SENS rattrape ce que le mot-cle rate,
tout en restant fidele a la doctrine (zero dep dans le coeur, similarite = confidence, le
seuil du Router fait le gating, hybride avec les reseaux exacts).

Embedder JOUET deterministe ci-dessous (zero dep) : il mappe des SYNONYMES vers la meme
dimension ("chat"/"felin"/"matou" -> felin) pour DEMONTRER le routage par le sens sans
installer de modele. En vrai, on injecte sentence-transformers / OpenAI / Ollama (voir
examples/semantic_routing.py). CybNodes ne depend de RIEN : c'est l'embedder qu'on branche.

Lancement : python tests/test_semantic.py   (ou `pytest`). Self-contained.
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import CybNodes, HybridNetwork, Result, SemanticNetwork, cosine  # noqa: E402
from cybnodes.networks import CalculNetwork, SavoirNetwork  # noqa: E402


def _deacc(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


# --- embedder JOUET : synonymes -> meme dimension (montre le SENS, pas le mot exact) ---
_CONCEPT = {
    "chat": "felin", "chats": "felin", "felin": "felin", "felins": "felin",
    "matou": "felin", "matous": "felin", "minet": "felin", "minou": "felin", "minous": "felin",
    "mange": "nourriture", "manger": "nourriture", "bouffe": "nourriture",
    "nourriture": "nourriture", "miam": "nourriture", "repas": "nourriture",
    "meteo": "meteo", "temps": "meteo", "pluie": "meteo", "climat": "meteo",
    "froid": "meteo", "chaud": "meteo", "dehors": "meteo",
}
_DIMS = sorted(set(_CONCEPT.values()))   # ['felin', 'meteo', 'nourriture']


def toy_embed(text):
    v = [0.0] * len(_DIMS)
    for w in re.findall(r"[a-z]+", _deacc(text)):
        c = _CONCEPT.get(w)
        if c:
            v[_DIMS.index(c)] += 1.0
    return v


def _cat():
    return SemanticNetwork(
        name="savoir-chat",
        utterances=["c'est quoi un chat", "parle-moi des chats", "les felins"],
        embedder=toy_embed,
        answer="Le chat est un petit felin domestique.",
        floor=0.35,
        kind="savoir",
    )


def test_cosine_pure_python():
    assert abs(cosine([1, 0, 0], [1, 0, 0]) - 1.0) < 1e-9       # identiques -> 1
    assert abs(cosine([1, 0, 0], [0, 1, 0])) < 1e-9             # orthogonaux -> 0
    assert cosine([], []) == 0.0                                 # vide -> 0 (jamais d'exception)
    assert cosine([1, 1], [1, 0, 0]) == 0.0                      # tailles differentes -> 0
    assert abs(cosine([2, 0], [5, 0]) - 1.0) < 1e-9             # meme direction, norme differente -> 1


def test_routes_by_meaning_not_keywords():
    """LE point : 'les matous' route vers le reseau chat SANS contenir le mot 'chat'."""
    cat = _cat()
    hit = cat.match("raconte-moi des trucs sur les matous")
    assert hit is not None, "le sens aurait du rattraper 'matous' (synonyme de chat)"
    assert hit.kind == "savoir" and hit.confidence >= 0.9
    # hors-sujet -> sous le floor -> DECLINE (le modele reprend), pas de faux positif
    assert cat.match("quel temps fait-il dehors ?") is None


def test_confidence_is_similarity_and_router_gates_it():
    """La similarite EST la confidence -> le seuil du Router (0.4.0) fait le gating, sans le toucher."""
    cat = SemanticNetwork("chat", utterances=["chat"], embedder=toy_embed,
                          answer="miaou", floor=0.1, kind="savoir")
    # 'chat' -> similarite 1.0 ; 'chat dehors' -> ~0.707 (felin + meteo)
    assert abs(cat.similarity("chat") - 1.0) < 1e-9
    assert 0.70 < cat.similarity("chat dehors") < 0.71
    # seuil 0.8 : 1.0 passe, 0.707 rend la main au conducteur (anti-embourbement)
    cyb = CybNodes(conductor=lambda q, c: "MODELE", networks=[cat], threshold=0.8)
    assert cyb.route_only("chat").kind == "savoir"
    assert cyb.route_only("chat dehors") is None and cyb.ask("chat dehors") == "MODELE"


def test_hybrid_exact_first_then_semantic():
    """HYBRIDE : le graphe exact prend 'c'est quoi un chat', le SENS rattrape 'les matous'."""
    graph = [{"s": "chat", "r": "est_un", "o": "animal"}, {"s": "chat", "r": "fait", "o": "miaou"}]
    hyb = HybridNetwork(SavoirNetwork(triples=graph), _cat())
    exact = hyb.match("c'est quoi un chat ?")
    assert exact is not None and exact.kind == "savoir" and "miaou" in exact.text   # voie graphe
    fuzzy = hyb.match("raconte-moi sur les matous")        # pas d'entite 'matou' au graphe...
    assert fuzzy is not None and fuzzy.kind == "savoir"     # ...le sens prend le relais
    assert "felin" in fuzzy.text                            # c'est bien la reponse semantique


def test_responder_confidence_is_capped_by_routing():
    """Un responder qui calcule la reponse voit sa confidence bornee par la certitude de routage."""
    def respond(q):
        return Result(kind="savoir", text="repondu", confidence=1.0)
    cat = SemanticNetwork("chat", utterances=["chat"], embedder=toy_embed,
                          responder=respond, floor=0.1)
    r = cat.match("chat dehors")           # routage ~0.707 -> borne la confidence du responder
    assert r is not None and 0.70 < r.confidence < 0.71


# --- metrique de routage (meme esprit que test_router.py) ---
_CASES = [
    ("combien font 7 x 8 ?",          "calcul"),   # exact deterministe
    ("c'est quoi un matou ?",         "savoir"),   # sens : synonyme de chat (regex raterait)
    ("les minous, ca mange quoi ?",   "savoir"),   # sens : 2 concepts, pas le mot 'chat'
    ("quel temps fait-il ?",          None),       # hors-domaine -> le modele reprend
    ("bonjour, comment ca va ?",      None),       # conversation -> le modele reprend
]


def test_routing_accuracy_semantic_plus_exact():
    cyb = CybNodes(conductor=lambda q, c: "MODELE", networks=[CalculNetwork(), _cat()])
    score, lines = 0, []
    for q, expected in _CASES:
        hit = cyb.route_only(q)
        got = hit.kind if hit is not None else None
        ok = got == expected
        score += ok
        lines.append("  [%s] %-32s -> %s (attendu %s)" % ("OK" if ok else "XX", q, got, expected))
    print("\n".join(lines))
    print("  routage semantique+exact : %d/%d" % (score, len(_CASES)))
    assert score == len(_CASES), "le routage par le sens s'est trompe sur au moins un cas"


def test_cosine_vecteurs_empoisonnes():
    # regression 0.6.0 : NaN/Inf ou composante non numerique -> 0.0 promis par la docstring,
    # jamais d'exception (un embedder fragile ne doit pas casser le routage ni le cache).
    from cybnodes import cosine
    assert cosine([float("nan"), 1.0], [1.0, 1.0]) == 0.0
    assert cosine([float("inf"), 1.0], [1.0, 1.0]) == 0.0
    assert cosine(["a", 1.0], [1.0, 1.0]) == 0.0
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0       # le chemin sain reste intact


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK  ", t.__name__)
    print("--- %d/%d tests passes ---" % (len(tests), len(tests)))
