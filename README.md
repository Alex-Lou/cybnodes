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
| **Routeur** | `Router` | choisit le réseau ; un réseau qui plante n'écroule rien |
| **Tisseur** | `Weaver` + `Persona` | redit le résultat brut dans la voix |
| **Mémoire** | `Memory` | capte des faits sûrs sur l'utilisateur (backend pluggable) |

---

## Les réseaux livrés

| Réseau | Ce qu'il fait | Vérifiable par |
|---|---|---|
| `CalculNetwork` | arithmétique exacte (`+ - × ÷ ^ %`, mots "fois / plus / puissance"…), AST sûr, **zéro `eval`** | le calcul lui-même |
| `SavoirNetwork` | **GraphRAG** : répond depuis un graphe de triplets `sujet-relation-objet` | le nœud du graphe |
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

Ce qui marche aujourd'hui, testé (`python tests/test_cybnodes.py`) :

- ✅ Cœur (routeur, tisseur/persona, mémoire, conducteur model-agnostic)
- ✅ `CalculNetwork`, `SavoirNetwork` (GraphRAG), `WebNetwork` (Brave)

Pistes ouvertes (design posé, pas encore livré, pas de promesse vide) :

- Routeur d'intention par classifieur (plutôt qu'ordre fixe)
- Réseaux code / langues / traduction
- Backends de recherche additionnels

---

## Licence

MIT, fais-en ce que tu veux.

<div align="center">

*Conçu par **CybWu**. Né autour d'une petite IA, pensé pour entourer n'importe quel modèle.*

🐺

</div>
