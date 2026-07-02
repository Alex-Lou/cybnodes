"""Tests du gate d'ANCRAGE : consensus (desaccord interne) + verifier optionnel + fail-safe."""
from cybnodes import Router
from cybnodes.networks import GroundingGate, RecallNetwork


def _recall(pairs, **kw):
    kw.setdefault("min_score", 0.3)
    return RecallNetwork(pairs=pairs, **kw)


def test_passe_plat_quand_consensus_ok():
    # un seul gold pertinent -> aucun desaccord -> le gate sert la reponse telle quelle.
    net = GroundingGate(_recall([("c'est quoi Pixar ?", "Pixar, c'est un studio d'animation.")]))
    r = net.match("c'est quoi Pixar")
    assert r is not None and "studio" in r.text


def test_abstient_sur_desaccord_interne():
    # "sang" attrape DEUX golds proches en score qui disent autre chose (coeur vs definition).
    pairs = [
        ("le sang c'est quoi ?", "Le coeur pompe le sang dans tout le corps."),
        ("a quoi sert le sang ?", "Le sang transporte l'oxygene et les nutriments."),
    ]
    brut = _recall(pairs)
    assert brut.match("le sang c'est quoi") is not None          # le reseau nu sert (a tort)
    gate = GroundingGate(brut)
    assert gate.match("le sang c'est quoi") is None              # le gate voit le conflit -> abstient


def test_sert_quand_les_proches_sont_d_accord():
    # deux golds proches qui disent LA MEME chose -> consensus -> on sert.
    pairs = [
        ("qui a peint la Joconde ?", "La Joconde a ete peinte par Leonard de Vinci."),
        ("qui est l'auteur de la Joconde ?", "La Joconde est une oeuvre de Leonard de Vinci."),
    ]
    gate = GroundingGate(_recall(pairs))
    r = gate.match("qui a peint la joconde")
    assert r is not None and "Vinci" in r.text


def test_consensus_desactivable():
    pairs = [
        ("le sang c'est quoi ?", "Le coeur pompe le sang dans tout le corps."),
        ("a quoi sert le sang ?", "Le sang transporte l'oxygene et les nutriments."),
    ]
    gate = GroundingGate(_recall(pairs), consensus=False)
    assert gate.match("le sang c'est quoi") is not None          # sans consensus -> passe-plat


def test_verifier_bloque_sous_le_seuil():
    net = GroundingGate(_recall([("c'est quoi Pixar ?", "un studio.")]),
                        verifier=lambda q, a: 0.1, min_entailment=0.5)
    assert net.match("c'est quoi Pixar") is None                 # ancrage juge faible -> abstention


def test_verifier_laisse_passer_au_dessus():
    net = GroundingGate(_recall([("c'est quoi Pixar ?", "un studio.")]),
                        verifier=lambda q, a: 0.9, min_entailment=0.5)
    assert net.match("c'est quoi Pixar") is not None


def test_verifier_qui_plante_ne_bloque_pas():
    def boom(q, a):
        raise RuntimeError("verifier casse")
    net = GroundingGate(_recall([("c'est quoi Pixar ?", "un studio.")]), verifier=boom)
    assert net.match("c'est quoi Pixar") is not None             # fail-safe : on sert quand meme


def test_abstention_interne_propagee():
    # le reseau interne s'abstient -> le gate aussi (rien a verifier).
    net = GroundingGate(_recall([("c'est quoi Pixar ?", "un studio.")], min_score=0.6))
    assert net.match("quelle est la meteo demain a Tokyo") is None


def test_fail_safe_sans_match_topk():
    # un reseau interne SANS match_topk : le consensus est ignore, le gate reste un passe-plat.
    from cybnodes.network import Network
    from cybnodes.result import Result

    class Bete(Network):
        name = "bete"
        def match(self, q):
            return Result(kind="savoir", text="reponse fixe", confidence=1.0)

    net = GroundingGate(Bete())
    r = net.match("n'importe quoi")
    assert r is not None and r.text == "reponse fixe"


def test_clusters_meme_sens_servi():
    # deux golds au SENS identique mais mots differents : le token-overlap crierait "conflit" ;
    # avec l'artefact de clusters (meme cluster) -> REDONDANCE -> on sert.
    pairs = [
        ("tu es une fille ?", "Ni fille ni garcon, je suis une IA."),
        ("es-tu une fille ?", "Ni l'un ni l'autre, je suis N3."),
    ]
    clusters = {"ni fille ni garcon, je suis une ia": 1, "ni l'un ni l'autre, je suis n3": 1}
    gate = GroundingGate(_recall(pairs), answer_clusters=clusters)
    r = gate.match("tu es une fille")
    assert r is not None                              # meme cluster -> plus de faux conflit


def test_clusters_sens_different_abstient():
    # deux golds de sens DIFFERENT (clusters distincts) partageant un mot -> vrai desaccord -> abstient.
    pairs = [
        ("le sang c'est quoi ?", "Le coeur pompe le sang."),
        ("a quoi sert le sang ?", "Le sang transporte l'oxygene."),
    ]
    clusters = {"le coeur pompe le sang.": 1, "le sang transporte l'oxygene.": 2}
    gate = GroundingGate(_recall(pairs), answer_clusters=clusters)
    assert gate.match("le sang c'est quoi") is None   # clusters differents -> abstention


def test_clusters_conflit_dur():
    # meme si les scores sont proches, une paire marquee CONTRADICTION force l'abstention.
    pairs = [
        ("il pleut ?", "Oui il pleut."),
        ("il pleut dehors ?", "Non il ne pleut pas."),
    ]
    clusters = {"oui il pleut.": 1, "non il ne pleut pas.": 1}   # meme cluster par erreur...
    gate = GroundingGate(_recall(pairs), conflict_pairs=[["Oui il pleut.", "Non il ne pleut pas."]],
                         answer_clusters=clusters)
    assert gate.match("il pleut") is None             # ...mais contradiction dure -> abstient


def test_clusters_repli_si_inconnu():
    # une reponse absente de l'artefact -> repli sur le token-overlap (fail-safe, comme avant).
    pairs = [("c'est quoi Pixar ?", "Pixar, c'est un studio d'animation.")]
    gate = GroundingGate(_recall(pairs), answer_clusters={"autre chose": 9})
    assert gate.match("c'est quoi Pixar") is not None  # inconnu du cluster -> repli tokens -> sert


def test_integration_routeur():
    pairs = [
        ("le sang c'est quoi ?", "Le coeur pompe le sang."),
        ("a quoi sert le sang ?", "Le sang transporte l'oxygene."),
        ("c'est quoi Pixar ?", "Pixar, c'est un studio d'animation."),
    ]
    router = Router([GroundingGate(_recall(pairs))])
    assert router.route("le sang c'est quoi") is None            # conflit -> le routeur passe la main
    r = router.route("c'est quoi Pixar")
    assert r is not None and "studio" in r.text                  # clair -> servi


def test_conflict_pairs_veto_en_mode_auto():
    # regression 0.6.0 : une contradiction DECLAREE (conflict_pairs) est un VETO meme dans le
    # repli lexical (mode auto sans clusters). Avant, deux reponses lexicalement PROCHES mais
    # declarees contradictoires (Canberra vs Sydney) etaient servies quand meme.
    pairs = [
        ("la capitale de l'Australie ?", "La capitale de l'Australie, c'est Canberra."),
        ("capitale de l'Australie, c'est quoi ?", "La capitale de l'Australie, c'est Sydney."),
    ]
    contradiction = [["La capitale de l'Australie, c'est Canberra.",
                      "La capitale de l'Australie, c'est Sydney."]]
    sans = GroundingGate(_recall(pairs))
    avec = GroundingGate(_recall(pairs), conflict_pairs=contradiction)
    assert sans.match("capitale de l'Australie") is not None    # proches en tokens -> servi (fusion)
    assert avec.match("capitale de l'Australie") is None        # contradiction declaree -> abstention
