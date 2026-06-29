"""Reseau CALCUL : arithmetique EXACTE.

Ce qu'un cerveau de LLM ne fait pas de maniere sure. On detecte une expression
(chiffres + operateurs, ou mots francais "fois/plus/divise par/puissance...") seulement
si elle relie au moins deux nombres, on l'evalue via un AST securise (aucun eval()),
et on renvoie un Result que le Tisseur redira dans la voix du conducteur.
"""
from __future__ import annotations

import ast
import operator
import re
from typing import Optional

from ..network import Manifest, Network
from ..result import Result

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}

# mots -> operateurs (appliques seulement si entre des nombres, cf _EXPR)
_WORD_OPS = [
    (re.compile(r"\bmultipli[ée]+ par\b", re.I), " * "),
    (re.compile(r"\bdivis[ée]+ par\b", re.I), " / "),
    (re.compile(r"\bpuissance\b", re.I), " ** "),
    (re.compile(r"\bmodulo\b", re.I), " % "),
    (re.compile(r"\bplus\b", re.I), " + "),
    (re.compile(r"\bmoins\b", re.I), " - "),
    (re.compile(r"\bfois\b", re.I), " * "),
]

# une vraie expression : >= deux nombres relies par des operateurs (** inclus)
_EXPR = re.compile(
    r"[-+]?\d[\d ]*(?:[.,]\d+)?(?:\s*(?:\*\*|[-+*/x×÷^%])\s*[-+]?\d[\d ]*(?:[.,]\d+)?)+"
)

# Gating d'INTENTION (ne pas calculer une date, une version, ou une phrase qui contient des chiffres).
# On ne prend la main que sur un vrai calcul : indice explicite (combien/calcule/...) OU expression
# isolee (quasi rien d'autre que des chiffres/operateurs). En cas de doute -> on rend la main au modele
# (un faux negatif est benin ; un faux positif livre une reponse fausse avec aplomb).
_CALC_CUE = re.compile(
    r"\bcombien\b|\bcalcule[rz]?\b|[cç]a fait|[ée]gale?|r[ée]sultat|\bfont\b|\bcu[aá]nto\b", re.I)
_DATE = re.compile(r"\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b|\b\d{4}-\d{1,2}-\d{1,2}\b")


def _is_real_calc(question: str, work: str) -> bool:
    if _DATE.search(question):                 # une date n'est pas un calcul
        return False
    if _CALC_CUE.search(question):
        return True
    body = re.sub(r"[0-9+\-*/x×÷^%=().,:;!?]", " ", work)   # ce qu'il reste hors chiffres/operateurs
    return len([w for w in body.split() if len(w) >= 2]) <= 1


def _guard_pow(base, exp):
    # anti-DoS : les entiers Python sont illimites, une puissance non bornee bloque CPU+RAM.
    if abs(exp) > 1000:
        raise ValueError("exposant hors borne")
    base_bits = base.bit_length() if isinstance(base, int) else 64
    if base_bits * (abs(exp) or 1) > 10000:
        raise ValueError("puissance trop grande")


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _safe_eval(node.left), _safe_eval(node.right)
        if type(node.op) is ast.Pow:
            _guard_pow(left, right)
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("expression non supportee")


def _clean(raw: str) -> str:
    # raw vient deja de _EXPR (chiffres + operateurs) : le 'x' y est forcement multiplicatif.
    s = raw.replace("×", "*").replace("x", "*").replace("÷", "/").replace("^", "**")
    return s.replace(",", ".").replace(" ", "")


class CalculNetwork(Network):
    name = "calcul"
    manifest = Manifest(
        answers="arithmetique exacte (+ - x / ^ %, et les mots fois/plus/divise par/puissance)",
        deterministic=True,    # un calcul est sa propre preuve, toujours reproductible
        needs_source=False,
        fallback="pass",
    )

    def match(self, question: str) -> Optional[Result]:
        work = question or ""
        for rx, op in _WORD_OPS:
            work = rx.sub(op, work)
        m = _EXPR.search(work)
        if not m:
            return None
        if not _is_real_calc(question or "", work):   # gating : vrai calcul, pas date/phrase deguisee
            return None
        expr = _clean(m.group(0))
        if not re.search(r"\*\*|[-+*/%]", expr):  # garde-fou : un vrai operateur
            return None
        try:
            value = _safe_eval(ast.parse(expr, mode="eval").body)
        except ZeroDivisionError:                 # honnete plutot que None (qui laisserait le LLM halluciner)
            return Result(kind="calcul_erreur", text="Division par zero : impossible.",
                          data={"expr": m.group(0).strip()}, source="calcul exact (AST)")
        except Exception:
            return None
        if isinstance(value, float):
            value = int(value) if value.is_integer() else round(value, 4)
        pretty = re.sub(r"\s*\*\*\s*", " ^ ", m.group(0).strip())
        pretty = re.sub(r"\s*\*\s*", " x ", pretty)
        return Result(
            kind="calcul",
            text="%s = %s" % (pretty, value),
            data={"expr": pretty, "value": value},
            source="calcul exact (AST)",
        )
