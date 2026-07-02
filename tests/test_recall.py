"""Tests du reseau RECUPERATION (rappel) : recuperation lexicale + abstention + confiance."""
from cybnodes import Router
from cybnodes.networks import RecallNetwork

PAIRS = [
    ("C'est quoi Pixar ?", "Pixar, c'est un studio d'animation americain.", "culture.txt"),
    ("Qui est Zeus dans la mythologie grecque ?", "Zeus, c'est le roi des dieux grecs."),
    ("Quelle est la capitale de la France ?", "La capitale de la France, c'est Paris."),
]


def test_retrieval_exact():
    r = RecallNetwork(pairs=PAIRS).match("c'est quoi Pixar")
    assert r is not None and "studio" in r.text
    assert r.confidence >= 0.9            # match quasi-exact -> haute confiance
    assert r.source == "culture.txt"      # source = tracabilite
    assert r.kind == "savoir"


def test_paraphrase_retrieves():
    r = RecallNetwork(pairs=PAIRS).match("la capitale de la France")
    assert r is not None and "Paris" in r.text


def test_fuzzy_typo_matches():
    # une faute de frappe dans un mot-cle est corrigee vers le vocab du corpus (Pixr -> Pixar)
    r = RecallNetwork(pairs=PAIRS).match("cest quoi Pixr")
    assert r is not None and "studio" in r.text


def test_fuzzy_off_abstains_on_typo():
    # fuzzy=False : comportement historique exact -> la faute ne matche pas (abstention)
    assert RecallNetwork(pairs=PAIRS, fuzzy=False).match("cest quoi Pixr") is None


def test_fuzzy_clean_query_unchanged():
    # une requete PROPRE se comporte a l'identique avec ou sans fuzzy -> ZERO regression
    a = RecallNetwork(pairs=PAIRS, fuzzy=True).match("c'est quoi Pixar")
    b = RecallNetwork(pairs=PAIRS, fuzzy=False).match("c'est quoi Pixar")
    assert a is not None and b is not None and a.text == b.text


def test_abstention_offtopic():
    assert RecallNetwork(pairs=PAIRS).match("quelle est la meteo demain a Tokyo") is None


def test_min_score_floor():
    # vaguement liee mais pas couverte -> sous le seuil -> None (abstention honnete)
    assert RecallNetwork(pairs=PAIRS, min_score=0.6).match("raconte une histoire grecque") is None


def test_router_integration():
    r = Router([RecallNetwork(pairs=PAIRS)]).route("qui est Zeus")
    assert r is not None and "dieux" in r.text


def test_confidence_gates_router():
    net = RecallNetwork(pairs=PAIRS, min_score=0.0)         # le reseau gradue sans plancher
    assert Router([net], threshold=0.95).route("explique moi Zeus le dieu grec") is None


def test_add_pairs_grows():
    net = RecallNetwork(pairs=PAIRS)
    n0 = len(net)
    net.add_pairs([("Qui a peint la Joconde ?", "Leonard de Vinci.")])
    assert len(net) == n0 + 1
    assert net.match("qui a peint la joconde") is not None


def test_match_topk_sorted():
    pairs = [
        ("Qui a peint la Joconde ?", "Leonard de Vinci l'a peinte."),
        ("Qui est l'auteur de la Joconde ?", "C'est bien Leonard de Vinci."),
        ("Quelle est la capitale de la France ?", "Paris."),
    ]
    top = RecallNetwork(pairs=pairs, min_score=0.3).match_topk("qui a peint la joconde", k=3)
    assert isinstance(top, list) and len(top) >= 1
    assert all(len(t) == 3 for t in top)                 # (score, reponse, source)
    assert top == sorted(top, key=lambda x: -x[0])       # tri decroissant
    assert "Vinci" in top[0][1]


def test_match_topk_offtopic_empty():
    assert RecallNetwork(pairs=[("c'est quoi Pixar ?", "un studio.")]).match_topk("quelle meteo demain") == []


def test_tie_break_prefers_tight_match():
    # requete courte couverte par DEUX golds (ex-aequo de couverture IDF) -> on prefere le plus
    # SERRE (question du gold la plus centree sur la requete), pas l'ordre d'insertion.
    pairs = [
        ("Quel temple grec est dedie a Athena ?", "C'est le Parthenon."),   # large -> perd l'ex-aequo
        ("Qui est Athena ?", "Athena, la deesse grecque de la sagesse."),   # serre -> gagne
    ]
    r = RecallNetwork(pairs=pairs, min_score=0.3).match("qui est Athena")
    assert r is not None and "deesse" in r.text
    top = RecallNetwork(pairs=pairs, min_score=0.3).match_topk("qui est Athena", k=2)
    assert "deesse" in top[0][1]                        # meme departage dans le top-k


def test_recites_not_rephrases():
    # la reponse servie est EXACTEMENT la chaine stockee (recitation, zero reformulation)
    stored = "Reponse stockee mot pour mot, telle quelle."
    r = RecallNetwork(pairs=[("question test unique", stored)]).match("question test unique")
    assert r is not None and r.text == stored


def test_calibrate_abstention_safe_fallback_on_thin_data():
    # 0.7.0 : sur peu de donnees + cible tres stricte, le controle ne peut RIEN garantir -> il se
    # TAIT (seuil > 1 = abstention totale) plutot que de promettre un risque qu'il ne tient pas.
    net = RecallNetwork(pairs=PAIRS)
    ex = [("c'est quoi Pixar", "Pixar, c'est un studio d'animation americain."),
          ("qui est Zeus", "Zeus, c'est le roi des dieux grecs."),
          ("quelle meteo demain a Tokyo", "HORS_CORPUS"),
          ("recette de la tarte tatin", "HORS_CORPUS")]
    tau, curve = net.calibrate_abstention(ex, target_error=0.01, confidence=0.99)
    assert isinstance(curve, list) and net.min_score == tau
    assert tau > 1.0                                   # abstention totale = repli SUR
    assert net.match("qui est Zeus") is None           # plus rien n'est servi (doctrine : se taire)


def test_calibrate_stricter_is_never_more_permissive():
    ex = [("c'est quoi Pixar", "Pixar, c'est un studio d'animation americain."),
          ("qui est Zeus", "Zeus, c'est le roi des dieux grecs."),
          ("la capitale de la France", "La capitale de la France, c'est Paris."),
          ("truc sans aucun rapport", "X"), ("autre hors sujet total", "Y")]
    lax = RecallNetwork(pairs=PAIRS)
    t_lax, _ = lax.calibrate_abstention(ex, target_error=0.5, confidence=0.8)
    strict = RecallNetwork(pairs=PAIRS)
    t_strict, _ = strict.calibrate_abstention(ex, target_error=0.05, confidence=0.99)
    assert t_strict >= t_lax                           # exiger moins d'erreur ne BAISSE jamais le seuil


def test_calibrate_serves_with_ample_clean_calibration():
    # beaucoup d'exemples PROPRES (erreur observee nulle, n grand) -> la borne descend sous la cible
    # -> le controle AUTORISE a servir (le mecanisme n'est pas vacuously toujours-abstention).
    net = RecallNetwork(pairs=PAIRS)
    clean = [("c'est quoi Pixar", "Pixar, c'est un studio d'animation americain."),
             ("qui est Zeus", "Zeus, c'est le roi des dieux grecs."),
             ("la capitale de la France", "La capitale de la France, c'est Paris.")] * 20
    tau, _ = net.calibrate_abstention(clean, target_error=0.2, confidence=0.9)
    assert tau <= 1.0 and net.match("qui est Zeus") is not None
