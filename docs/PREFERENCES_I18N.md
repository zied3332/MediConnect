# Préférences et langues

La page `/preferences/` est accessible depuis les menus du site, du patient et des tableaux de bord professionnels. Elle propose les thèmes clair/sombre et les langues anglais, français et arabe.

Les choix sont conservés pendant un an dans les cookies `mediconnect_theme` et `django_language` de ce navigateur. Ils restent disponibles après déconnexion. Ils ne sont pas synchronisés entre appareils. Le formulaire utilise la protection CSRF de Django, une liste de valeurs autorisées et une validation des éventuelles redirections.

## Fonctionnement

- `core/preferences.py` fournit le formulaire, la vue et le contexte du thème.
- `LocaleMiddleware` sélectionne la langue avant le rendu des vues. Les catalogues Django traduisent les templates, les formulaires, les libellés des modèles et les erreurs.
- `/jsi18n/` expose les traductions des messages JavaScript. Les données variables sont interpolées après traduction.
- Les deux templates de base ajoutent les attributs `lang`, `dir` et `data-theme`. `static/css/theme.css` applique le thème et le sens de lecture arabe à toutes les pages qui les utilisent.
- Le patient conserve sa navigation de site ; les médecins et administrateurs conservent leur barre latérale. En arabe, celle-ci passe à droite.
- Les diagnostics, notes, messages personnels, noms et documents médicaux restent dans leur langue d'origine. Les traductions ne réécrivent aucune donnée clinique.

## Catalogues

Les catalogues compilés `.mo` sont inclus dans `locale/{en,fr,ar}/LC_MESSAGES/` ; aucune API de traduction n'est appelée pendant la navigation. Les fichiers `.po` restent éditables pour la relecture linguistique. Les traductions initiales ont été assistées par IA ; une relecture humaine, notamment de l'arabe et des termes médicaux, est recommandée avant une diffusion publique.

Après modification de textes d'interface, ajouter des marqueurs `{% translate %}`, `{% blocktranslate %}` ou `gettext`, collecter les textes et compléter les traductions :

```powershell
python scripts/collect_ui_markers.py
python scripts/build_ui_catalogs.py --translate
```

L'option `--translate` utilise la configuration Anthropic du serveur et envoie uniquement les textes statiques du catalogue ; elle peut consommer du crédit API. Sans cette option, le script compile le cache existant et refuse les textes manquants. Redémarrer le serveur après recompilation des catalogues pour vider le cache de traduction.

```powershell
python manage.py test core.test_preferences --keepdb --noinput
```

Pour ajouter un écran : hériter de l'un des templates de base, marquer tout son texte d'interface, utiliser des variables CSS de surface/texte et vérifier les trois langues avec les deux thèmes. Un nom de spécialité ajouté librement par un administrateur garde son nom d'origine tant qu'aucune traduction n'est ajoutée au catalogue.
