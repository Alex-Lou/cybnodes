# Changelog

Toutes les versions notables de CybNodes. Format inspiré de Keep a Changelog, versionnage SemVer.

## [0.6.0]

La release de la **fiabilité de la récupération**. Cinq briques qui composent une chaîne : router par le **sens** (pas que le mot-clé), **récupérer et réciter** une réponse validée (jamais reformulée), **vérifier l'ancrage** avant de servir, **nuancer** la voix quand la confiance est basse, et **ne pas rejouer** deux fois la même question. Tout reste zéro-dépendance, model-agnostic, et rétrocompatible.

### Ajouté

- **Routage par le sens — `SemanticNetwork` / `HybridNetwork`.** Router par le SENS, pas seulement par mots-clés : « les matous, ça mange quoi ? » route vers le réseau chat sans contenir le mot « chat ». L'`embedder` (texte → vecteur) est **injecté** (sentence-transformers, OpenAI, Ollama, maison…) → le cœur ne dépend toujours de RIEN. La **similarité cosinus** (pur Python) DEVIENT la `confidence`, donc le `threshold` du Router (0.4.0) fait le gating « décline-quand-tu-doutes » sans toucher au routeur ; sous le `floor`, le réseau rend la main. `HybridNetwork` combine, pour UNE capacité, la voie EXACTE d'abord (regex/déterministe) puis le SENS en repli — précision du mot-clé quand il matche, robustesse du sens sinon. Les prototypes sont plongés UNE fois (au `__init__`).

- **Cache sémantique calibré — `SemanticCache`.** Répond à une question déjà vue (ou très proche) sans rejouer réseaux/web/modèle — gros gain perf/coût sur un hôte lent (CPU). **Deux étages** : EXACT (même question normalisée → réponse identique, sans perte, marche SANS embedder) et SÉMANTIQUE (cosinus ≥ seuil, embedder injecté). Seuil **conservateur** par défaut (0.95) car un faux hit = servir une réponse proche-mais-fausse = mentir. `calibrate(positifs, négatifs, target_false_hit_rate)` dérive LE SEUIL de TES données (balaye 0→1, prend le plus bas qui tient le faux-hit-rate cible) et renvoie la courbe inspectable. Ne cache **jamais l'incertitude** (`min_confidence`), TTL pour le temps-sensible, `stats()`. Composant autonome (tu l'enroules autour de ton conducteur).

- **`RecallNetwork` — récupération lexicale qui RÉCITE.** Répond depuis un corpus de paires question/réponse **déjà validées**, par recherche lexicale **pondérée par la rareté (IDF, comme BM25)** : matcher un mot rare et discriminant (« Zeus », « Pixar ») pèse fort, matcher un mot banal (« demain », « chose ») pèse peu. Il **récite** la réponse stockée — il ne la reformule JAMAIS — donc sur le chemin « trouvé », l'hallucination est structurellement impossible. Sous `min_score` il DÉCLINE (aveu d'ignorance > fausse mémoire confiante). Départage des ex-æquo par Jaccard (préfère le gold le plus serré : +6,3 pts d'exactitude sur les requêtes courtes). `match_topk()` expose les k meilleurs candidats (le socle du GroundingGate). Mémoire non-paramétrique qui GRANDIT (`add_pairs`), réversible, 100% déterministe.
  - **Tolérance aux fautes de frappe** (`fuzzy=True`, par défaut) : un mot de la REQUÊTE absent du corpus est corrigé vers le token connu le plus proche (distance d'édition ≤ 1 pour les mots courts, ≤ 2 pour les longs, early-exit). « c'est quoi Pixr » retrouve « Pixar ». La correction ne touche QUE la requête, jamais l'index → une requête propre reste identique (`fuzzy=False` restaure l'exact).
  - `stopwords=` / `synonyms=` (déjà configurables depuis 0.2.0) permettent d'y brancher les mots-outils d'une autre langue (espagnol : `sobre`, `para`, `como`…) ou des abréviations SMS, sans changer le code.

- **`GroundingGate` — vérifier l'ANCRAGE avant de servir.** Même à score élevé, un match lexical peut répondre À CÔTÉ (« le sang, c'est quoi ? » attrape un gold sur le cœur qui pompe le sang : score haut, sujet faux) — l'erreur est SÉMANTIQUE, pas lexicale, et le seuil seul ne la voit pas (~7-9 % de réponses fausses restent). Le gate enveloppe un réseau et vérifie AVANT de servir, avec deux mécanismes composables et **tous deux fail-safe** : (1) **consensus** (frugal, zéro dépendance) — il regarde les k meilleurs golds ; si des candidats proches en score se CONTREDISENT, la question est ambiguë → abstention (désaccord INTERNE au corpus, mesurable sans aucun modèle) ; (2) **verifier optionnel** — un callable `(question, réponse) → 0..1` (petit NLI CPU branché plus tard) ; sous le seuil → abstention. Sans `match_topk` ni verifier, le gate est un simple passe-plat (comportement inchangé) → il ne peut RIEN casser. Il n'ôte QUE des réponses douteuses, n'en invente aucune. Détection de conflit par **clusters d'entropie sémantique** (`answer_clusters` pré-calculés hors-ligne) ou repli lexical, plus paires de **contradiction dure** (`conflict_pairs`).

- **Nuance par confiance dans le Weaver (hedging).** Sous un seuil de confiance, la voix ADMET le doute (« je ne suis pas tout à fait sûre, mais je crois que… {value} ») au lieu d'asséner un fait incertain avec aplomb. `Weaver(hedge_below=0.6)` ; phrases surchargeables via `Weaver(hedges=[...])` ou `persona.templates["_hedge"]`. Complète l'abstention DURE du routeur (0.4.0) par une abstention DOUCE côté présentation. Défaut `hedge_below=0.0` → jamais de nuance (comportement historique).

### Durci (audit adverse pré-release)
- `Weaver._hedge()` ne plante plus quand `result.data` porte une clé `value`/`source` (p.ex. le calcul) : les champs réservés sont posés APRÈS les data, même pattern que `_render`.
- `cosine()` tient sa promesse « jamais d'exception » : NaN/Inf ou composante non numérique → `0.0` (un embedder fragile ne casse ni le routage ni le cache).
- `GroundingGate` : une contradiction déclarée via `conflict_pairs` est un **veto** même dans le repli lexical (mode `auto` sans clusters) — le paramètre n'est plus inerte dans sa configuration par défaut.
- `SemanticCache.calibrate()` refuse des `positives`/`negatives` vides (`ValueError`, même style que le garde embedder) au lieu de poser silencieusement `threshold=0.0` — qui aurait servi n'importe quel faux hit.

### Compatibilité
- **100 % rétrocompatible.** Tout est opt-in ou inerte par défaut : `threshold=0.0`, `hedge_below=0.0`, cache non câblé d'office, nouveaux réseaux à instancier soi-même ; sur une requête PROPRE, `fuzzy=True` et `fuzzy=False` donnent le MÊME résultat. Le cœur reste **stdlib-only** (les embedders sont injectés, jamais importés). Tests verts : **71/71** (`test_cybnodes`, `test_router`, `test_semantic`, `test_cache`, `test_recall`, `test_grounding`, `test_weaver` — dont 4 tests de régression du durcissement).

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
