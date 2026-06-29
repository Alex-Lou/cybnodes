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


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
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
        expr = _clean(m.group(0))
        if not re.search(r"\*\*|[-+*/%]", expr):  # garde-fou : un vrai operateur
            return None
        try:
            value = _safe_eval(ast.parse(expr, mode="eval").body)
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
