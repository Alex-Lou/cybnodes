"""Tests du Weaver : nuance par confiance (hedging) + citation de source. Retrocompatible."""
from cybnodes import Persona, Result, Weaver


def _r(text="Paris.", conf=1.0, source=None):
    return Result(kind="savoir", text=text, source=source, confidence=conf)


def test_no_hedge_by_default():
    # hedge_below=0.0 -> jamais de nuance, meme a confiance basse (comportement historique)
    assert Weaver().weave(_r(conf=0.1)) == "Paris."


def test_hedge_below_threshold():
    out = Weaver(hedge_below=0.6).weave(_r(conf=0.3))
    assert "Paris." in out and out != "Paris."   # le doute est exprime, le fait reste present


def test_no_hedge_above_threshold():
    assert Weaver(hedge_below=0.6).weave(_r(conf=0.9)) == "Paris."   # confiant -> pas de nuance


def test_cite_source():
    out = Weaver(cite=True).weave(_r(source="geo.txt"))
    assert "geo.txt" in out


def test_custom_hedges():
    out = Weaver(hedge_below=0.5, hedges=["Peut-etre {value} ?"]).weave(_r(text="Paris", conf=0.2))
    assert out == "Peut-etre Paris ?"


def test_persona_hedge_template_wins():
    p = Persona(templates={"_hedge": ["Mmh, {value}, je crois."]})
    out = Weaver(persona=p, hedge_below=0.5).weave(_r(text="Paris", conf=0.1))
    assert out == "Mmh, Paris, je crois."


def test_hedge_and_cite_combine():
    out = Weaver(cite=True, hedge_below=0.6).weave(_r(text="Paris", conf=0.3, source="geo.txt"))
    assert "Paris" in out and "geo.txt" in out and out != "Paris"


def test_hedge_survives_data_value_key():
    # regression 0.6.0 : un Result dont data porte "value"/"source" (p.ex. CalculNetwork) faisait
    # planter _hedge en TypeError (kwarg en double dans format). Meme pattern que _render desormais.
    r = Result(kind="calcul", text="47 x 38 = 1786", source="calcul exact", confidence=0.2,
               data={"value": 1786, "source": "interne"})
    out = Weaver(hedge_below=0.6).weave(r)
    assert "1786" in out and out != "47 x 38 = 1786"   # nuance exprimee, zero crash
