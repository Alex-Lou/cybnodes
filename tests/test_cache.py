"""Cache SEMANTIQUE calibre : prouve les deux etages (exact sans-perte, semantique conservateur),
la SINCERITE (ne cache pas l'incertitude, seuil conservateur), le TTL, et surtout la COURBE de
calibration (methode validee : balayer le seuil sur des paires etiquetees et choisir le plus bas
qui tient un faux-hit-rate cible).

Lancement : python tests/test_cache.py   (ou `pytest`). Self-contained.
"""
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybnodes import Result, SemanticCache, cosine  # noqa: E402


# --- embedder JOUET concept (felin/meteo/nourriture) pour l'etage semantique ---
_CONCEPT = {"chat": "felin", "chats": "felin", "felin": "felin", "felins": "felin",
            "matou": "felin", "matous": "felin",
            "mange": "nourriture", "mangent": "nourriture", "manger": "nourriture",
            "temps": "meteo", "pluie": "meteo", "dehors": "meteo"}
_DIMS = sorted(set(_CONCEPT.values()))


def toy_embed(text):
    t = "".join(c for c in unicodedata.normalize("NFD", (text or "").lower())
                if unicodedata.category(c) != "Mn")
    v = [0.0] * len(_DIMS)
    for w in re.findall(r"[a-z]+", t):
        if w in _CONCEPT:
            v[_DIMS.index(_CONCEPT[w])] += 1.0
    return v


def _res(txt="reponse", conf=1.0):
    return Result(kind="test", text=txt, confidence=conf)


def test_exact_stage_is_lossless_without_embedder():
    """Sans embedder, l'etage EXACT marche deja (meme question normalisee -> meme reponse)."""
    c = SemanticCache()  # pas d'embedder -> seul l'exact
    c.put("Combien font 7 x 8 ?", _res("56"))
    assert c.get("combien font 7 x 8 ?").text == "56"     # casse/ponctuation/accents ignores
    assert c.get("  COMBIEN  font 7 x 8 ?  ").text == "56"
    assert c.get("combien font 9 x 9 ?") is None           # vraie difference -> miss


def test_semantic_stage_conservative():
    """Etage semantique : une paraphrase proche fait hit ; une proche-mais-differente, miss."""
    c = SemanticCache(embedder=toy_embed, threshold=0.95)
    c.put("c'est quoi un chat ?", _res("Le chat est un felin."))
    assert c.get("parle-moi des matous").text == "Le chat est un felin."   # synonyme -> hit
    assert c.get("quel temps fait-il dehors ?") is None                    # autre sens -> miss


def test_never_caches_uncertainty():
    """Sincerite : un Result de confiance basse n'est JAMAIS fige (sinon on perennise un doute)."""
    c = SemanticCache(min_confidence=0.5)
    c.put("question floue", _res("peut-etre...", conf=0.3))
    assert c.get("question floue") is None                 # pas cache (confiance < 0.5)
    c.put("question sure", _res("certain", conf=0.9))
    assert c.get("question sure").text == "certain"        # cache (confiance suffisante)


def test_ttl_expiry():
    """TTL : une entree expiree (web/temps-sensible) n'est plus servie."""
    c = SemanticCache(ttl=10)
    c.put("info du jour", _res("frais"), now=1000.0)
    assert c.get("info du jour", now=1005.0).text == "frais"   # dans la fenetre
    assert c.get("info du jour", now=1011.0) is None           # expire (>10s)


# --- embedder CONTROLE (vecteurs a cosinus connus) pour demontrer LA COURBE ---
_VEC = {
    "p1a": [1.0, 0.0],   "p1b": [1.0, 0.0],          # cos 1.00  (positif : meme reponse)
    "p2a": [1.0, 0.0],   "p2b": [0.97, 0.2431],      # cos ~0.97 (positif)
    "n1a": [1.0, 0.0],   "n1b": [0.6, 0.8],          # cos 0.60  (negatif franc)
    "n2a": [1.0, 0.0],   "n2b": [0.9, 0.4359],       # cos 0.90  (FAUX AMI : tres proche, autre reponse)
}


def _ctrl_embed(s):
    return _VEC.get(s, [0.0, 0.0])


def test_calibration_curve_excludes_the_false_friend():
    """LA COURBE : avec une cible de faux-hit-rate = 0, calibrate() doit choisir un seuil qui
    EXCLUT le faux ami (negatif a 0.90) -- sinon le cache mentirait."""
    pos = [("p1a", "p1b"), ("p2a", "p2b")]   # cosinus ~1.00 et ~0.97
    neg = [("n1a", "n1b"), ("n2a", "n2b")]   # cosinus 0.60 et 0.90 (le 0.90 est le piege)
    c = SemanticCache(embedder=_ctrl_embed)
    thr, curve = c.calibrate(pos, neg, target_false_hit_rate=0.0)
    maxneg = max(cosine(_ctrl_embed(a), _ctrl_embed(b)) for a, b in neg)   # le faux ami (~0.90)
    minpos = min(cosine(_ctrl_embed(a), _ctrl_embed(b)) for a, b in pos)   # le positif le plus bas (~0.97)
    # le seuil doit passer AU-DESSUS du faux ami mais SOUS les positifs -> on garde le hit
    assert thr > maxneg, "le seuil doit exclure le faux ami"
    assert thr <= minpos, "...sans jeter les vrais positifs"
    # a ce seuil : faux-hit-rate nul, et on capte encore les positifs
    row = next(r for r in curve if abs(r["threshold"] - thr) < 1e-9)
    assert row["false_hit_rate"] == 0.0 and row["hit_rate"] >= 0.5
    # cible plus permissive -> seuil PLUS BAS (plus de hits, au prix d'un faux hit tolere)
    thr_loose, _ = c.calibrate(pos, neg, target_false_hit_rate=0.5)
    assert thr_loose < thr
    print("  seuil cible-0%% = %.2f (faux ami a %.3f)  |  seuil cible-50%% = %.2f" % (thr, maxneg, thr_loose))


def test_calibration_curve_is_monotone_and_reported():
    """La courbe est inspectable (tracable) : faux-hit-rate decroit quand le seuil monte."""
    c = SemanticCache(embedder=_ctrl_embed)
    _, curve = c.calibrate([("p1a", "p1b")], [("n2a", "n2b")], target_false_hit_rate=0.0)
    fhrs = [r["false_hit_rate"] for r in curve]
    assert all(fhrs[i] >= fhrs[i + 1] for i in range(len(fhrs) - 1))   # monotone decroissant
    assert curve[0]["threshold"] == 0.0 and curve[-1]["threshold"] == 1.0


def test_calibrate_refuse_paires_vides():
    # regression 0.6.0 : negatives=[] posait threshold=0.0 (l'etage semantique servait n'importe
    # quel cosinus > 0 = faux hits garantis). Desormais calibrate exige positives ET negatives,
    # et un appel invalide ne detruit pas le seuil en place.
    c = SemanticCache(embedder=_ctrl_embed)
    for pos, neg in ([[], [("a", "b")]], [[("a", "b")], []]):
        try:
            c.calibrate(pos, neg)
            assert False, "calibrate aurait du refuser des paires vides"
        except ValueError:
            pass
    assert c.threshold == 0.95             # le seuil conservateur n'a pas ete touche


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("OK  ", t.__name__)
    print("--- %d/%d tests passes ---" % (len(tests), len(tests)))
