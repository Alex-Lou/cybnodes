"""Reseau WEB : recherche d'actualite / faits externes via l'API Brave Search (tier gratuit).

Se declenche seulement sur une INTENTION de recherche (cherche / actualite / recent /
aujourd'hui / en ligne...). Honnete : la reponse dit "j'ai cherche" et porte la SOURCE (URL).
Degrade proprement : sans cle API, `match` renvoie None -> le modele repond comme avant.

Cle : variable d'env `BRAVE_API_KEY` (https://brave.com/search/api/ , tier gratuit). Aucune
dependance externe (urllib stdlib). `fetch` est injectable -> testable sans reseau ni cle.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from typing import Callable, Optional

from ..network import Network
from ..result import Result

_INTENT = re.compile(
    r"\bcherche?\b|\bactualit|\bnews\b|quoi de neuf|r[eé]cent|derni[eè]re?s? nouvelles"
    r"|en ce moment|aujourd'?hui|ce qui se passe|\bgoogle\b|sur internet|en ligne",
    re.I,
)


class WebNetwork(Network):
    name = "web"
    ENDPOINT = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: Optional[str] = None, env_var: str = "BRAVE_API_KEY",
                 max_results: int = 3, timeout: int = 8,
                 fetch: Optional[Callable[[str], dict]] = None):
        self.api_key = api_key or os.environ.get(env_var)
        self.max_results = max_results
        self.timeout = timeout
        self._fetch = fetch or self._http  # injectable pour les tests

    def _http(self, query: str) -> dict:
        url = self.ENDPOINT + "?" + urllib.parse.urlencode({"q": query, "count": self.max_results})
        req = urllib.request.Request(url, headers={
            "X-Subscription-Token": self.api_key or "",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.load(resp)

    def match(self, question: str) -> Optional[Result]:
        q = (question or "").strip()
        if not q or not _INTENT.search(q):
            return None
        if not self.api_key:
            return None  # pas de cle -> on laisse le modele repondre (pas de fausse promesse)
        try:
            data = self._fetch(q)
        except Exception:
            return None
        results = ((data or {}).get("web", {}) or {}).get("results", [])[:self.max_results]
        if not results:
            return None
        top = results[0]
        snippet = re.sub(r"<[^>]+>", "", top.get("description", "") or "").strip()
        text = "J'ai cherche, et voila ce que j'ai trouve : %s" % (snippet or top.get("title", ""))
        return Result(
            kind="web",
            text=text,
            data={"query": q, "title": top.get("title", ""), "snippet": snippet,
                  "results": [{"title": r.get("title"), "url": r.get("url")} for r in results]},
            source=top.get("url"),
        )
