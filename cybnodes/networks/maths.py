"""Reseau MATHS : calcul symbolique EXACT (derivee, integrale, limite, equation, simplification).

Ce qu'un LLM tente mais rate souvent au-dela du lycee. On detecte une INTENTION math avancee
(derive / integre / limite / resous / simplifie / factorise / developpe) accompagnee d'une
expression, on l'evalue via sympy (symbolique, exact), et on renvoie un Result que le Tisseur
redira dans la voix du conducteur.

Dependance OPTIONNELLE : `pip install cybnodes[math]` (sympy). Sans sympy, match() renvoie None
-> le modele repond comme avant (degradation propre, fidele au principe "core stdlib-only").
"""
from __future__ import annotations

import re
from typing import Optional

from ..network import Manifest, Network
from ..result import Result

try:
    import sympy as _sp
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations,
        implicit_multiplication_application, convert_xor,
    )
    _TRANSF = standard_transformations + (implicit_multiplication_application, convert_xor)
    _HAS_SYMPY = True
except Exception:  # sympy non installe -> le reseau se tait
    _HAS_SYMPY = False

# --- intentions (ordre = priorite). Le motif consomme le MOT ENTIER (\w*) pour ne pas laisser
#     de residu francais ("integrale" -> on retire tout, pas seulement "integr"). ---
_OPS = [
    ("derivee",     re.compile(r"d[ée]riv\w*", re.I)),
    ("integrale",   re.compile(r"int[ée]gr\w*|primitives?|∫", re.I)),
    ("limite",      re.compile(r"\blimites?\b|\blim\b", re.I)),
    ("resoudre",    re.compile(r"r[ée]sou\w*|[ée]quations?|solutions?", re.I)),
    ("factoriser",  re.compile(r"factoris\w*", re.I)),
    ("developper",  re.compile(r"d[ée]velopp\w*", re.I)),
    ("simplifier",  re.compile(r"simplifi\w*", re.I)),
]

# mots de remplissage francais a retirer (mots ENTIERS) avant de parser l'expression. Tout ce qui
# n'est ni un nombre, ni un operateur, ni une variable (1 lettre), ni une fonction connue est du bruit.
_FILLER = re.compile(
    r"\b(calcule[rz]?|donne[rsz]?|trouve[rz]?|quelles?|quels?|est|combien|vaut|font?|"
    r"les?|la|l|j|qu|du|des|de|en|fonction|par|rapport|[aà]|il|te|pla[iî]t|stp|svp|merci|"
    r"peux|tu|pour|moi|cette|cet|ce|une?|et|ou|the|of|please|quand|tend|vers|approche|entre|from|to)\b",
    re.I)

# "limite ... quand x tend vers <point>"
_LIM_POINT = re.compile(r"(?:quand\s+)?([a-z])\s*(?:->|→|tend\s+vers|approche\s+de)\s*"
                        r"(\+?\s*inf(?:ini|ty)?|-\s*inf(?:ini|ty)?|[-+]?\d+(?:[.,]\d+)?|0)", re.I)
# bornes d'integrale definie : "de A a B" / "entre A et B" / "from A to B"
_BOUNDS = re.compile(r"(?:de|entre|from)\s+([-+]?\d+(?:[.,]\d+)?)\s+(?:[aà]|et|to)\s+([-+]?\d+(?:[.,]\d+)?)", re.I)
# variable d'integration/derivation explicite : "dx/dy/dz/dt" (PAS "de"/"du" francais), "par rapport a y"
_DVAR = re.compile(r"\bd([xyzt])\b|par\s+rapport\s+[aà]\s+([a-z])", re.I)


def _norm(s: str) -> str:
    s = s.replace("√", "sqrt").replace("×", "*").replace("÷", "/").replace("·", "*").replace("²", "^2").replace("³", "^3")
    return s


def _parse(expr_str: str):
    expr_str = expr_str.strip().strip(".?!,; ")
    if not expr_str:
        return None
    try:
        e = parse_expr(expr_str, transformations=_TRANSF, evaluate=True)
        # refuse un parse trivial qui ne contient ni variable ni operation (ex: un simple nombre)
        return e
    except Exception:
        return None


def _grab_expr(text: str, op: str):
    """Extrait la chaine d'expression mathematique du message (apres avoir retire les mots francais)."""
    t = _norm(text)
    var = None
    # retire le mot d'operation lui-meme (entier)
    for name, rx in _OPS:
        if name == op:
            t = rx.sub(" ", t)
    # pour la limite : isole "quand x tend vers <point>", recupere la variable ET le point
    point = None
    if op == "limite":
        m = _LIM_POINT.search(t)
        if m:
            var, point = m.group(1), m.group(2)
            t = t[:m.start()] + " " + t[m.end():]
    # bornes d'integrale definie ("de A a B")
    bounds = None
    if op == "integrale":
        mb = _BOUNDS.search(t)
        if mb:
            bounds = (mb.group(1), mb.group(2))
            t = t[:mb.start()] + " " + t[mb.end():]
    # variable explicite (dx / par rapport a y)
    mv = _DVAR.search(t)
    if mv:
        var = var or mv.group(1) or mv.group(2)
        t = _DVAR.sub(" ", t)
    t = re.sub(r"\b[a-zA-Z]{1,4}'", " ", t)             # elisions : l' d' qu' s' n' ...
    t = _FILLER.sub(" ", t)                             # mots francais entiers
    t = re.sub(r"[^0-9a-zA-Z_.^*/+\-()=,√ ]", " ", t)   # ne garde que le math (apostrophes deja parties)
    t = re.sub(r"\s+", " ", t).strip()
    return t, var, point, bounds


def _pick_var(expr, hint):
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    if hint:
        for s in syms:
            if s.name == hint:
                return s
    for s in syms:
        if s.name == "x":
            return s
    return syms[0] if syms else _sp.Symbol("x")


def _pt(val: str):
    v = (val or "").lower().replace(" ", "")
    if "inf" in v:
        return _sp.oo if not v.startswith("-") else -_sp.oo
    return _sp.Rational(str(val).replace(",", "."))


def _fmt(e) -> str:
    try:
        return _sp.sstr(e)
    except Exception:
        return str(e)


class MathNetwork(Network):
    name = "maths"
    manifest = Manifest(
        answers="maths symboliques exactes : derivee, integrale, limite, equation, simplification (sympy)",
        deterministic=True,    # un calcul symbolique est sa propre preuve
        needs_source=False,
        fallback="pass",       # sans sympy ou si l'expression ne se parse pas, on rend la main
    )

    def match(self, question: str) -> Optional[Result]:
        if not _HAS_SYMPY:
            return None
        q = question or ""
        op = next((name for name, rx in _OPS if rx.search(q)), None)
        if not op:
            return None
        expr_str, var_hint, point, bounds = _grab_expr(q, op)
        if not expr_str:
            return None
        try:
            if op == "resoudre":
                # equation : "lhs = rhs" -> lhs-rhs = 0 ; sinon expr = 0
                if "=" in expr_str:
                    lhs, rhs = expr_str.split("=", 1)
                    lhs, rhs = _parse(lhs), _parse(rhs)
                    if lhs is None or rhs is None:
                        return None
                    eqn = _sp.Eq(lhs, rhs)
                    expr = lhs - rhs
                else:
                    expr = _parse(expr_str)
                    if expr is None:
                        return None
                    eqn = _sp.Eq(expr, 0)
                var = _pick_var(expr, var_hint)
                sols = _sp.solve(eqn, var)
                if not sols:
                    return None
                pretty = ", ".join("%s = %s" % (var, _fmt(s)) for s in sols)
                text = "Solutions : %s" % pretty
                data = {"op": "resoudre", "var": str(var), "solutions": [_fmt(s) for s in sols]}
            else:
                expr = _parse(expr_str)
                if expr is None or (not expr.free_symbols and op in ("derivee", "integrale", "limite")):
                    return None
                var = _pick_var(expr, var_hint)
                if op == "derivee":
                    res = _sp.diff(expr, var)
                    text = "La derivee de %s est %s" % (_fmt(expr), _fmt(res))
                elif op == "integrale":
                    if bounds:
                        a, b = _pt(bounds[0]), _pt(bounds[1])
                        res = _sp.integrate(expr, (var, a, b))
                        text = "L'integrale de %s de %s a %s vaut %s" % (_fmt(expr), bounds[0], bounds[1], _fmt(res))
                    else:
                        res = _sp.integrate(expr, var)
                        text = "Une primitive de %s est %s + C" % (_fmt(expr), _fmt(res))
                elif op == "limite":
                    if point is None:
                        return None
                    res = _sp.limit(expr, var, _pt(point))
                    text = "La limite de %s quand %s tend vers %s vaut %s" % (_fmt(expr), var, point, _fmt(res))
                elif op == "factoriser":
                    res = _sp.factor(expr)
                    text = "%s = %s" % (_fmt(expr), _fmt(res))
                elif op == "developper":
                    res = _sp.expand(expr)
                    text = "%s = %s" % (_fmt(expr), _fmt(res))
                else:  # simplifier
                    res = _sp.simplify(expr)
                    text = "%s = %s" % (_fmt(expr), _fmt(res))
                data = {"op": op, "var": str(var), "expr": _fmt(expr), "result": _fmt(res)}
        except Exception:
            return None
        return Result(kind="maths", text=text, data=data, source="calcul symbolique (sympy)")
