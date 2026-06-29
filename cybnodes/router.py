"""Router : lit l'intention via les reseaux, choisit le premier qui prend la main.

Regles d'abord (fiable), modele ensuite. Un reseau qui leve une exception est ignore
(fail-safe) : il ne doit jamais faire tomber tout le circuit.

Garde-fou anti-embourbement (la lecon `_is_real_calc`) : un reseau DECLINE (renvoie None,
ou un Result de confiance basse) des qu'il n'est pas sur. Le routeur n'accepte un Result que
si sa `confidence` atteint `threshold` ; en dessous, on passe la main comme si c'etait None
-> au reseau suivant, puis au modele (qui repond avec aisance, honnete dans le doute). Mieux
vaut un faux negatif (le modele reprend) qu'un faux positif (une reponse fausse avec aplomb).

`threshold = 0.0` par defaut : tout Result passe, comportement historique inchange. Le seuil
sert surtout aux reseaux FLOUS (savoir par similarite, web) qui graduent leur certitude ; les
reseaux deterministes (calcul) restent en tout-ou-rien via leur propre garde (-> None).
"""
from __future__ import annotations

from typing import List, Optional

from .network import Network
from .result import Result


class Router:
    def __init__(self, networks: Optional[List[Network]] = None, threshold: float = 0.0):
        self.networks: List[Network] = list(networks or [])
        self.threshold: float = threshold

    def add(self, network: Network) -> "Router":
        self.networks.append(network)
        return self

    def route(self, question: str) -> Optional[Result]:
        for net in self.networks:
            try:
                result = net.match(question)
            except Exception:
                result = None  # un reseau fragile ne casse jamais le circuit
            if result is not None and result.confidence >= self.threshold:
                return result
            # result en dessous du seuil = pas assez sur -> on passe la main (comme None)
        return None
