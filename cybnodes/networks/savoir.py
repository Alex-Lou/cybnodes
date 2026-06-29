"""Reseau SAVOIR (GraphRAG) : repond depuis un graphe de connaissances (triplets sujet-relation-objet).

Le savoir vit HORS du modele -> on le corrige/etend en editant le graphe, sans re-entrainer.
Le reseau ne se declenche que sur une INTENTION de savoir (c'est quoi / qu'est-ce que / a quoi
ca sert...) ET si une entite connue (sujet d'au moins un triplet) apparait dans la question.
Il compose alors une phrase a partir des triplets de cette entite, que le Tisseur revoix.

Graphe attendu : {"triples": [{"s": "...", "r": "...", "o": "..."}, ...]} ou directement la liste.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import List, Optional

from ..network import Manifest, Network
from ..result import Result


def _deacc(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", (s or "").lower())
        if unicodedata.category(c) != "Mn"
    )


# verbalisation des relations -> phrase lisible (vocabulaire controle, extensible)
_REL_VERB = {
    "est_un": "est un", "est_une": "est une", "partie_de": "fait partie de",
    "sert_a": "sert a", "fait": "fait", "mange": "mange", "vit_dans": "vit dans",
    "a": "a", "a_besoin_de": "a besoin de", "aime": "aime", "cause": "cause",
    "devient": "devient", "donne": "donne", "contraire_de": "est le contraire de",
    "plus_grand_que": "est plus grand que", "vient_de": "vient de",
    "vient_dans": "se trouve dans", "vient_apres": "vient apres",
}

_INTENT = re.compile(
    r"c'?est quoi|qu'?est[- ]?ce|c'?est qui|\bquel(?:le|s|les)?\b|connais[- ]?tu|sais[- ]?tu"
    r"|parle[- ]?moi|raconte|\bdefinition\b|decri|a quoi (?:ca |ca |)sert|ca sert a quoi",
    re.I,
)


class SavoirNetwork(Network):
    name = "savoir"
    manifest = Manifest(
        answers="faits depuis ton graphe de connaissances (triplets sujet-relation-objet)",
        deterministic=True,    # le graphe est la source de verite, reponse stable
        needs_source=True,     # la reponse devrait pointer le node utilise
        fallback="pass",
    )

    def __init__(self, triples: Optional[List[dict]] = None,
                 graph_path: Optional[str] = None,
                 min_entity_len: int = 3,
                 max_clauses: int = 4):
        if graph_path:
            with open(graph_path, encoding="utf-8") as fh:
                data = json.load(fh)
            triples = data.get("triples", []) if isinstance(data, dict) else data
        self.triples: List[dict] = list(triples or [])
        self.min_entity_len = min_entity_len
        self.max_clauses = max_clauses
        self._by_subject: dict = {}
        for t in self.triples:
            s = t.get("s")
            if s:
                self._by_subject.setdefault(_deacc(s), []).append(t)

    def _find_entity(self, question: str) -> Optional[str]:
        words = [w for w in re.split(r"[^a-z0-9]+", _deacc(question)) if w]
        cands = [w for w in words if len(w) >= self.min_entity_len and w in self._by_subject]
        return max(cands, key=len) if cands else None  # le mot connu le plus long

    def match(self, question: str) -> Optional[Result]:
        q = question or ""
        if not _INTENT.search(_deacc(q)):
            return None
        ent = self._find_entity(q)
        if not ent:
            return None
        facts = self._by_subject.get(ent, [])
        if not facts:
            return None
        label = facts[0]["s"]
        clauses = []
        for t in facts[:self.max_clauses]:
            verb = _REL_VERB.get(t["r"], t["r"].replace("_", " "))
            clauses.append("%s %s" % (verb, t["o"]))
        text = "%s %s." % (label.capitalize(), ", ".join(clauses))
        return Result(
            kind="savoir",
            text=text,
            data={"entity": label,
                  "facts": [[t["s"], t["r"], t["o"]] for t in facts[:self.max_clauses]]},
            source="graphe de connaissances : %s" % label,   # le node utilise -> tracable
        )
