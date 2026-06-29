# Changelog

Toutes les versions notables de CybNodes. Format inspiré de Keep a Changelog, versionnage SemVer.

## [0.5.0]

Le seuil livre en 0.4.0 devient enfin utile : les reseaux flous graduent leur confiance au lieu de toujours renvoyer 1.0. Un sujet riche et specifique, ou une intention forte, inspire plus de confiance qu'un signal pauvre ou ambigu.

### Ajoute
- **SavoirNetwork gradue sa confiance** selon la richesse (nombre de faits utilises) et la specificite (longueur du sujet) : un savoir appuye sur plusieurs faits et un mot plus long, donc moins ambigu, monte plus haut qu'un fait unique sur un mot court.
- **WebNetwork gradue sa confiance** selon la force de l'intention (cherche, actualite, news vs un signal faible comme "aujourd'hui") et la qualite du resultat (presence d'un extrait, nombre de resultats). Effet : le sur-declenchement web devient maitrisable par le seuil, sans retirer l'intention (donc rien ne casse).
- Les **reseaux deterministes** (calcul, maths) restent a confiance 1.0 : un resultat exact merite une confiance pleine.

### Compatibilite
- 100% retrocompatible : la confidence est une metadonnee ; avec threshold=0.0 par defaut le routage est identique a 0.4.0. Tests verts : 9/9 (`test_router`, dont `test_threshold_bites_real_savoir`) + 11/11 (`test_cybnodes`, dont `test_savoir_confidence` et `test_web_confidence`).

## [0.4.0]

Le routeur sait désormais quand un réseau n'est pas sûr et passe la main proprement.

### Ajouté
- **Seuil de confiance** : `Router(networks, threshold=0.0)` et `CybNodes(..., threshold=...)`. Le routeur ne retient un `Result` que si sa `confidence` atteint le seuil (sinon il passe la main au réseau suivant, puis au modèle). Le champ `Result.confidence` (présent depuis 0.2.0) est maintenant honoré.
- **Doctrine anti-embourbement** documentée dans le contrat `Network` : un réseau décline dès qu'il doute (None pour les réseaux déterministes comme le calcul, confidence basse pour les réseaux flous comme savoir/web). Mieux vaut laisser le modèle reprendre (honnête dans le doute) que livrer une réponse fausse avec aplomb.

### Compatibilité
- 100% rétrocompatible : `threshold=0.0` par défaut donne le comportement 0.3.0 inchangé. Tests verts : 8/8 (`test_router`, dont 3 nouveaux sur le seuil) + 9/9 (`test_cybnodes`).

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
