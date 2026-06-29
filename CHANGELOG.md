# Changelog

Toutes les versions notables de CybNodes. Format inspiré de Keep a Changelog, versionnage SemVer.

## [0.3.0]

Nouveau réseau : les **maths avancées** (ce qu'un petit modèle rate au-delà de l'arithmétique).

### Ajouté
- **`MathNetwork`** : calcul **symbolique EXACT** via sympy — dérivées, intégrales (indéfinies et définies), limites, résolution d'équations, simplification / factorisation / développement. Se déclenche sur l'intention (`dérive`, `intègre`, `limite`, `résous`, `simplifie`, `factorise`, `développe`) + une expression ; sinon il rend la main au modèle.
- Dépendance **optionnelle** : `pip install cybnodes[math]` (sympy). Sans sympy, `MathNetwork` se tait proprement (`match()` → `None`) — le **cœur reste stdlib-only**.

### Note d'intégration
- Place `MathNetwork` **avant** `CalculNetwork` dans le routeur (le maths gère `résous x^2 = ...`, le calcul gère l'arithmétique pure). Les deux ne se marchent pas dessus.

## [0.2.1]

Tour de robustesse et de sécurité. Un calcul ne se déclenche que sur une vraie intention, jamais sur une date ou une phrase, et on ne peut plus faire exploser le process avec une puissance géante.

### Sécurité
- **Borne anti-DoS sur les puissances** : `9**9**9` ou `2**999999999` ne sont plus évalués (les entiers Python sont illimités, donc blocage CPU/RAM). Au-delà des bornes, le réseau rend la main au modèle.

### Modifié
- **Gating d'intention du calcul** : `CalculNetwork` ne prend plus la main sur une date (`12/05/2024`) ni une phrase qui contient des chiffres (`3+3 tu es belle`). Il faut un vrai calcul : expression isolée, ou un indice (`combien`, `calcule`, `ça fait`...). En cas de doute, le modèle répond.
- **Division par zéro honnête** : `5 / 0` renvoie un message clair ("Division par zéro : impossible.") au lieu de passer silencieusement la main et de laisser le modèle halluciner.

### Ajouté
- **Cache du réseau web** : `WebNetwork(cache_ttl=900)` mémorise les réponses identiques (TTL configurable) pour éviter les appels facturés redondants à l'API.

### Compatibilité
- 100% rétrocompatible. Les 13 tests passent (8 dans `test_cybnodes`, 5 dans `test_router`).

## [0.2.0]

Tour de fiabilité, suite à un retour de la communauté : le routeur est le produit, et un
petit modèle devient digne de confiance quand l'outil prend la main au bon moment et que la
réponse montre sa preuve.

### Ajouté
- **Évidence dans la réponse** : `Weaver(cite=True)` fait remonter la source (calcul exact,
  node du graphe, URL) dans la réponse finale. `{source}` est aussi un champ de gabarit pour
  un placement fin. Défaut `cite=False` (aucun changement de comportement).
- **Manifeste de capacité** : `Manifest` (answers / deterministic / needs_source / fallback)
  déclaré par chaque réseau, introspectable via `CybNodes.skills()`. Purement déclaratif.
- **Router evals** : `tests/test_router.py` mesure que le routeur choisit la bonne capacité
  sur des catégories franches (calcul simple, calcul dans une phrase, info récente, fait
  connu, fait inconnu, conversation), via `route_only()`.

### Modifié
- `SavoirNetwork` : la source nomme désormais le node utilisé (`graphe de connaissances : X`).

### Compatibilité
- 100% rétrocompatible. Les 6 tests d'origine passent tels quels.

## [0.1.0]

Première version : cœur model-agnostic (conducteur, routeur, tisseur/persona, mémoire) et
les réseaux `CalculNetwork`, `SavoirNetwork` (GraphRAG), `WebNetwork` (Brave Search).
