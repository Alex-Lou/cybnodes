# Changelog

Toutes les versions notables de CybNodes. Format inspiré de Keep a Changelog, versionnage SemVer.

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
