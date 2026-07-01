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
