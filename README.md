<div align="center">

# CybNodes

**On n'alourdit pas le cerveau par force brute. On l'entoure de circuits structurés et vérifiables.**

Une petite librairie Python qui entoure ton LLM de **réseaux de capacités** (calcul exact, savoir, recherche web), et qui redit chaque résultat **dans la voix de ton modèle**.

[![PyPI](https://img.shields.io/pypi/v/cybnodes)](https://pypi.org/project/cybnodes/)

**[cybnodes.pages.dev](https://cybnodes.pages.dev)** / [GitHub](https://github.com/Alex-Lou/cybnodes) / [PyPI](https://pypi.org/project/cybnodes/) / MIT

</div>

---

## C'est quoi, concrètement ?

CybNodes est une **librairie Python** (`pip install cybnodes`, puis `import cybnodes`). Pas une app, pas un service, pas un script à lancer : une **brique que tu branches autour de ton propre modèle**.

L'idée : un LLM est génial pour *parler*, mauvais pour *garantir*. Il invente un calcul, hallucine une date, n'a pas l'actu. Plutôt que de grossir le modèle, CybNodes met devant lui des **réseaux**, chacun sait répondre de façon **exacte et vérifiable** à un type de question. Un **routeur** choisit le bon réseau ; un **tisseur** redit le résultat brut dans la voix de ton modèle pour garder son âme.

> Conséquence : un petit modèle (qui tient sur ta machine) peut alimenter un système qui "pèse" bien plus lourd.

Pour le dire autrement : CybNodes n'est pas un mini-LangChain. C'est une petite **couche de fiabilité pour les petits modèles locaux**. Les petits modèles sont attachants ; la fiabilité vient de savoir *quand* le modèle doit arrêter de deviner et passer la main à un outil précis.

---

## Pourquoi

| Sans CybNodes | Avec CybNodes |
|---|---|
| "47 × 38 ?" → le LLM tente, parfois faux | calcul **exact** (AST sûr), toujours juste |
| "c'est quoi un X ?" → le LLM hallucine | réponse depuis **ton graphe de connaissances** |
| "quoi de neuf sur Y ?" → données périmées | **recherche web** avec la source citée |
| corriger un fait → ré-entraîner le modèle | éditer un **fichier**, zéro entraînement |

Le savoir et les capacités vivent **hors du modèle**. Tu les corriges, tu les étends, sans toucher aux poids.

---

## Installation

```bash
pip install cybnodes
# ou, depuis les sources :
git clone https://github.com/Alex-Lou/cybnodes.git
cd cybnodes && pip install -e .
```

Python ≥ 3.9. **Aucune dépendance obligatoire** (stdlib uniquement, le réseau web utilise `urllib`).

---

## Démarrage (60 secondes)

```python
from cybnodes import CybNodes, Persona
from cybnodes.networks import CalculNetwork, SavoirNetwork

# 1. Tu apportes TON modèle : n'importe quel callable (ollama, API, local…)
def mon_llm(question, context):
    return appelle_mon_modele(question, context)   # -> str

# 2. Tu l'entoures de réseaux
cyb = CybNodes(
    conductor=mon_llm,
    networks=[
        CalculNetwork(),                              # calcul exact
        SavoirNetwork(graph_path="mon_graphe.json"),  # GraphRAG sur tes triplets
    ],
    persona=Persona(name="Aria", templates={
        "calcul": ["Voilà : {value} ✦", "{value}, et c'est exact !"],
        "savoir": ["{value}"],
    }),
)

# 3. Tu demandes
cyb.ask("combien font 47 x 38 ?")   # → "Voilà : 47 x 38 = 1786 ✦"   (exact, jamais faux)
cyb.ask("c'est quoi un chat ?")     # → depuis ton graphe, dans la voix d'Aria
cyb.ask("écris-moi un haïku")       # → aucun réseau ne prend la main → ton modèle répond
```

C'est tout. Le routeur essaie les réseaux ; si aucun ne répond, ton modèle reprend la main, comme avant.

---

## L'architecture en 5 couches

```
        question
           │
   ┌───────▼────────┐
   │   ROUTEUR      │  essaie les réseaux dans l'ordre (règles d'abord, fiable)
   └───────┬────────┘
     hit?  │  no hit
   ┌───────▼──┐   └──────────────┐
   │ RÉSEAU   │                  │
   │ (calcul, │            ┌─────▼──────┐
   │  savoir, │            │ CONDUCTEUR │  ton LLM (sa voix)
   │  web…)   │            └─────┬──────┘
   └───────┬──┘                  │
   ┌───────▼────────┐            │
   │   TISSEUR      │ redit dans │
   │  + PERSONA     │ la voix    │
   └───────┬────────┘            │
           └──────────┬──────────┘
                   réponse
```

| Couche | Classe | Rôle |
|---|---|---|
| **Conducteur** | `conductor=` (ton callable) | ton modèle, sa voix/personnalité |
| **Réseaux** | `Network` | une capacité chacun, indépendants |
| **Routeur** | `Router` | choisit le réseau (seuil de confiance optionnel) ; un réseau qui plante n'écroule rien |
| **Tisseur** | `Weaver` + `Persona` | redit le résultat brut dans la voix |
| **Mémoire** | `Memory` | capte des faits sûrs sur l'utilisateur (backend pluggable) |

---

## Les réseaux livrés

| Réseau | Ce qu'il fait | Vérifiable par |
|---|---|---|
| `CalculNetwork` | arithmétique exacte (`+ - × ÷ ^ %`, mots "fois / plus / puissance"…), AST sûr, **zéro `eval`**, puissances bornées, ne se déclenche pas sur une date ou une phrase | le calcul lui-même |
| `MathNetwork` | **maths symboliques** : dérivées, intégrales, limites, équations, simplification / factorisation (sympy) — `pip install cybnodes[math]` | le calcul symbolique exact |
| `SavoirNetwork` | **GraphRAG** : répond depuis un graphe de triplets `sujet-relation-objet` | le nœud du graphe |
| `RecallNetwork` | **récupération lexicale** (pondérée IDF) dans un corpus de Q/R validées : **récite** la réponse stockée (jamais reformulée → zéro hallucination sur le chemin trouvé), tolère les fautes de frappe, s'abstient sous le seuil | la paire Q/R stockée |
| `GroundingGate` | **enveloppe** un réseau et vérifie l'ancrage AVANT de servir : consensus des golds proches (+ verifier NLI optionnel) ; n'ôte que le douteux, n'invente rien, fail-safe | le désaccord interne du corpus |
| `WebNetwork` | recherche d'actu via l'API **Brave Search** (clé `BRAVE_API_KEY`), cite la source | l'URL renvoyée |

Chaque réseau ne se déclenche que quand il est sûr de lui ; sinon il rend la main (renvoie `None`).

---

## Écrire ton propre réseau

```python
from cybnodes import Network, Result

class MeteoNetwork(Network):
    name = "meteo"

    def match(self, question):
        if "météo" not in question.lower():
            return None                       # pas mon rayon → je rends la main
        data = appel_api_meteo(...)           # un résultat VÉRIFIABLE (source réelle)
        return Result(kind="meteo", text=f"Il fait {data}°", source="api-météo")

cyb.add_network(MeteoNetwork())               # branché. C'est tout.
```

---

## Fiabilité : évidence, manifeste, evals

**La source dans la réponse.** Chaque `Result` porte une **source** (le calcul exact, le node du graphe, l'URL). Par défaut elle reste disponible mais discrète ; avec `Weaver(cite=True)` (ou un gabarit qui place `{source}`), elle remonte dans la réponse finale. C'est ce qui rend un petit modèle *fiable* et pas seulement charmant.

```python
from cybnodes import CybNodes, Weaver, Persona
cyb = CybNodes(conductor=mon_llm, networks=[...], weaver=Weaver(Persona(name="Aria"), cite=True))
cyb.ask("c'est quoi un chat ?")   # -> "... (source : graphe de connaissances : chat)"
```

**Le manifeste.** Chaque réseau peut déclarer ce qu'il sait faire : utile pour la doc, le debug, et un routeur futur. Purement déclaratif (ça ne change pas `match()`).

```python
from cybnodes import Manifest

class MeteoNetwork(Network):
    name = "meteo"
    manifest = Manifest(answers="la meteo d'une ville", deterministic=False, needs_source=True)
    ...

cyb.skills()   # -> [{'name': 'calcul', 'deterministic': True, 'needs_source': False, ...}, ...]
```

**Évaluer le routeur.** Le routeur EST le produit : ce qui compte, c'est qu'il choisisse la bonne capacité, et que la réponse reste dans ce que la capacité a prouvé. `route_only(question)` renvoie la décision brute (sans modèle ni tissage) ; `tests/test_router.py` mesure ça sur des cas francs (calcul simple, calcul caché dans une phrase, info récente, fait connu, fait inconnu, conversation). Comme le routeur est à base de règles, son point faible est le **rappel** : un `match()` qui rate un cas le laisse filer au modèle (ainsi le mot "aujourd'hui" peut encore sur-déclencher le web). D'où les evals.

**Le seuil de confiance (0.4.0).** Chaque `Result` porte une `confidence` (entre 0 et 1, défaut 1.0). Le routeur l'honore via un seuil : `Router(networks, threshold=0.6)` (ou `CybNodes(..., threshold=0.6)`). Un réseau déterministe (le calcul) décline en rendant `None` ; un réseau flou (savoir, web) peut répondre avec une confidence basse. Si cette confidence est sous le seuil, le routeur ne retient pas le résultat et passe la main au réseau suivant, puis au modèle. C'est la doctrine anti-embourbement : décliner quand on doute, plutôt que livrer une réponse fausse avec aplomb. Par défaut `threshold=0.0`, donc tout résultat passe et le comportement reste celui des versions précédentes.

```python
from cybnodes import CybNodes
# en dessous de 0.6 de confiance, le réseau passe la main (au suivant, puis au modèle)
cyb = CybNodes(conductor=mon_llm, networks=[...], threshold=0.6)
```

```python
from cybnodes import Result
# un réseau flou qui n'est pas sûr rend une confidence basse, plutôt que de bluffer
return Result(kind="savoir", text="...", source="graphe", confidence=0.3)
```

**Maintenant graduée pour de vrai (0.5.0).** En 0.4.0 le seuil était armé mais inerte : tous les réseaux renvoyaient `confidence=1.0`, donc rien ne tombait jamais sous le seuil. En 0.5.0, les deux réseaux flous notent leur propre confiance, ce qui rend le seuil utile en pratique. `SavoirNetwork` gradue selon la richesse et la spécificité du sujet (plusieurs faits et un mot plus long, donc moins ambigu, inspirent plus de confiance qu'un fait unique ou un mot court) ; `WebNetwork` gradue selon la force de l'intention (cherche / actualité = fort, "aujourd'hui" = faible) et la qualité du résultat (extrait présent, plusieurs hits). Les réseaux déterministes (calcul, maths) restent à 1.0. Un seuil bien placé écarte alors un savoir bâti sur un seul fait, ou une recherche web à intention faible, sans rien retirer du déclenchement.

```python
from cybnodes import CybNodes
from cybnodes.networks import SavoirNetwork

cyb = CybNodes(conductor=mon_llm, networks=[SavoirNetwork(graph_path="g.json")], threshold=0.85)
# "c'est quoi un chat ?"   -> 3 faits dans le graphe -> confidence 0.9 -> passe (>= 0.85)
# "c'est quoi le soleil ?" -> 1 seul fait            -> confidence 0.8 -> écarté (< 0.85), le modèle reprend la main
```

**Router par le sens, cacher, nuancer (0.6.0).** Trois renforts, tous zéro-dépendance et opt-in (l'embedder est toujours *injecté* — le cœur ne dépend de rien) :

```python
from cybnodes import SemanticNetwork, HybridNetwork, SemanticCache, Weaver
from cybnodes.networks import RecallNetwork, GroundingGate

# 1. Routage par le SENS : "les matous" route vers le réseau chat, sans le mot "chat".
#    La similarité cosinus devient la confidence -> le seuil du routeur la gate, sans changement.
chat = SemanticNetwork("savoir-chat", utterances=["c'est quoi un chat", "les félins"], embedder=emb)
savoir = HybridNetwork(SavoirNetwork(graph_path="g.json"), chat)   # mot-clé d'abord, sens en repli

# 2. Récupérer + réciter des réponses VALIDÉES, puis vérifier l'ancrage avant de servir.
recall = GroundingGate(RecallNetwork(pairs=[("c'est quoi Pixar ?", "Pixar, un studio d'animation.")]))
recall.match("cest quoi Pixr")        # -> récite "Pixar…" (faute corrigée), None si des golds proches divergent

# 3. Cache sémantique CALIBRÉ : ne rejoue pas une question déjà vue, sans jamais figer l'incertitude.
cache = SemanticCache(embedder=emb)   # deux étages (exact + sémantique) ; calibrate() dérive le seuil de tes données

# 4. Nuance (hedging) : sous le seuil de confiance, la voix ADMET le doute au lieu d'asséner.
weaver = Weaver(hedge_below=0.6)      # "je crois que… {value}"  (0.0 par défaut = jamais, historique)
```

---

## Quand l'utiliser (et quand non)

**Utilise CybNodes quand** tu veux qu'un LLM réponde de façon **exacte / vérifiable / à jour** sur certains types de questions, tout en gardant **sa voix**, sans ré-entraîner.

**Ne l'utilise pas** pour du pur génératif libre (écriture, brainstorming) : là, ton modèle seul suffit, CybNodes lui laisse simplement la main.

---

## Les 4 questions (les invariants)

- **Où vit l'état ?** Personnalité → conducteur ; savoir → graphe (hors modèle) ; faits utilisateur → Mémoire.
- **Où vit le feedback ?** Chaque réseau renvoie un résultat *vérifiable* (calcul exact, nœud du graphe, source web).
- **Qu'est-ce qui casse si on retire X ?** Réseaux indépendants → on en retire un sans casser les autres.
- **Timing / ordre ?** Routeur synchrone : 1 question → routeur → réseau(x) → tisseur → réponse.

---

## État du projet

Ce qui marche aujourd'hui, testé (`python -m pytest` — 74/74) :

- ✅ Cœur (routeur, tisseur/persona, mémoire, conducteur model-agnostic)
- ✅ `CalculNetwork`, `SavoirNetwork` (GraphRAG), `WebNetwork` (Brave)
- ✅ **Évidence** : la source remonte dans la réponse (`Weaver(cite=True)` / `{source}`)
- ✅ **Manifeste** : chaque réseau déclare sa capacité (`Manifest`, `cyb.skills()`)
- ✅ **Router evals** : `route_only()` + un fichier de tests par catégorie
- ✅ **Sécurité & gating (0.2.1)** : puissances bornées (anti-DoS), le calcul ne se déclenche plus sur une date ou une phrase, division par zéro honnête, cache du réseau web
- ✅ **Routage par confiance (0.4.0)** : `Router(threshold=...)` honore `Result.confidence` ; sous le seuil, le réseau passe la main (au suivant, puis au modèle). Rétrocompatible : `threshold=0.0` par défaut
- ✅ **Confiance graduée des réseaux flous (0.5.0)** : `SavoirNetwork` note selon la richesse / spécificité du sujet, `WebNetwork` selon la force de l'intention et la qualité du résultat ; le seuil de 0.4.0 devient donc utile en pratique. Déterministes (calcul, maths) à 1.0, rétrocompatible à seuil 0
- ✅ **Routage par le sens (0.6.0)** : `SemanticNetwork` / `HybridNetwork`, embedder **injecté** (zéro dep), similarité cosinus = `confidence` gatée par le seuil du routeur ; hybride « mot-clé d'abord, sens en repli »
- ✅ **Cache sémantique calibré (0.6.0)** : `SemanticCache` deux étages (exact sans-perte + sémantique conservateur), `calibrate()` **dérive** le seuil de tes données au lieu de le deviner, ne cache jamais l'incertitude, TTL
- ✅ **`RecallNetwork` (0.6.0)** : rappel lexical pondéré IDF depuis un corpus Q/R validé, **récite** (zéro hallucination sur le chemin trouvé), s'abstient sous le seuil, tolère les fautes de frappe (`fuzzy=True`, « Pixr » → « Pixar »), `stopwords`/`synonyms` pour une autre langue ou du SMS
- ✅ **`GroundingGate` (0.6.0)** : vérifie l'ancrage avant de servir (consensus des golds proches + verifier NLI optionnel), fail-safe, n'ôte que le douteux — n'invente rien
- ✅ **Nuance par confiance / hedging (0.6.0)** : `Weaver(hedge_below=...)` fait admettre le doute à la voix sous le seuil au lieu d'asséner ; rétrocompatible (`0.0` = jamais).
- ✅ **Seuil d'abstention conformal (0.7.0)** : `RecallNetwork.calibrate_abstention(examples, target_error, confidence)` calibre `min_score` avec une garantie **finie-échantillon** (Hoeffding + union bound) — « ne pas dépasser tel taux d'erreur » devient **prouvable sur tes données** ; repli sûr (abstention totale) si la cible est intenable. 74/74 tests verts

Pistes ouvertes (design posé, pas encore livré, pas de promesse vide) :

- Routeur d'intention par classifieur (plutôt qu'ordre fixe) ; l'arbitrage par `Result.confidence` et le seuil est désormais livré, le classifieur reste à faire
- Précision du routeur : resserrer les intentions trop larges (ex. "aujourd'hui")
- Réseaux code / langues / traduction
- Backends de recherche additionnels

---

## Licence

MIT, fais-en ce que tu veux.

<div align="center">

*Conçu par **CybWu**. Né autour d'une petite IA, pensé pour entourer n'importe quel modèle.*

🐺

</div>
