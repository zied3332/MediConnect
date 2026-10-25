# Module consultations, messages et avis

## IA : miroir de consultation

Le médecin peut préparer une fiche de lecture en trois rubriques : constats, consignes et suivi. Le brouillon est produit par Claude à partir des seuls champs `diagnostic` et `notes`. Le formulaire demande confirmation de leur transmission à Anthropic. Les identifiants du patient ne sont pas ajoutés automatiquement, mais le médecin doit vérifier qu'ils ne figurent pas dans le texte libre. Démonstration uniquement sur des données fictives.

Configuration serveur dans `.env`, jamais dans Git :

```dotenv
ANTHROPIC_API_KEY=cle_personnelle
ANTHROPIC_MODEL=claude-sonnet-4-5
```

Après récupération : `python manage.py migrate`. La quatrième table du module, `PatientBrief`, conserve le brouillon, sa version, son état, les citations, le temps de génération et la publication médicale.

Parcours : compte rendu → Préparer la fiche patient → confirmer la transmission → génération → comparer les rubriques et les sources → corriger → confirmer la vérification → publier. Le patient ne voit aucune proposition avant validation. Si le diagnostic ou les notes changent, la fiche est masquée au patient jusqu'à une nouvelle génération et validation. Une nouvelle génération retire aussi la version précédemment publiée jusqu'à sa validation.

Les citations doivent être des extraits exacts des champs sources. Les rubriques absentes portent « Non précisé dans le compte rendu ». La validation des citations ne prouve pas la fidélité sémantique de la reformulation : le médecin doit vérifier les négations, hypothèses, dates, unités, doses et omissions. Aucune recommandation nouvelle ne doit être ajoutée.

Le contrôle accepte les variantes typographiques d'apostrophes et d'espacement (espaces insécables, tabulations et retours à la ligne). La citation enregistrée et affichée est toujours récupérée dans le texte original. Aucun remplacement de mot, de chiffre, d'accent ou de négation n'est effectué pour rechercher une correspondance.

États : en préparation, à vérifier, indisponible, validé. L'interface affiche une animation et interroge un endpoint d'état. Le traitement est lancé avec `transaction.on_commit` dans Celery. Avec `CELERY_TASK_ALWAYS_EAGER=True`, le mode local exécute l'appel dans le processus web : l'interface reste animée, mais la requête HTTP attend. Pour un vrai traitement différé : Redis, `CELERY_TASK_ALWAYS_EAGER=False`, puis `celery -A config worker --pool=solo -l info` sous Windows. Il faut redémarrer le serveur et le worker après changement de clé.

Les délais, clé refusée, modèle indisponible, limitation de débit, échec de file et réponse invalide donnent des messages distincts. Pas de publication automatique, pas d'exception brute ni de contenu clinique journalisé par cet adaptateur. Le transport utilise la vérification TLS et les autorités de confiance du système. Aucun appel API réel n'est exécuté par les tests automatisés.

### Preuves pour la grille IA

- Pertinence : faciliter la lecture du compte rendu, sans remplacer le médecin.
- Intégration : adaptateur serveur `ai.py`, tâche Celery, vues dédiées, clé d'environnement et permissions de propriétaire.
- Expérience : progression, attente, échec explicite, citations dépliables et validation avant publication.
- Performance : durée réelle enregistrée pour chaque génération. Un essai réel sur un texte fictif a produit trois rubriques en environ 3,7 secondes le 25 octobre 2026 ; ce résultat unique n'est pas un benchmark.
- Évaluation : les tests contrôlent les sources exactes et les rubriques manquantes. Pour évaluer la qualité, constituer un jeu fictif annoté et compter séparément les omissions et les affirmations sans support par relecture humaine. Aucun score clinique n'est revendiqué à partir des seuls tests techniques.

Documentation du fournisseur : https://platform.claude.com/docs/en/api/messages/create

## Installation

Après récupération du code et activation de l'environnement :

```shell
python manage.py migrate
python manage.py test consultations
python manage.py runserver
```

## Démonstration

1. Médecin approuvé : Appointments → rendez-vous confirmé ou terminé → Rédiger / modifier la consultation.
2. Enregistrer un diagnostic obligatoire, des notes partagées et un lien HTTPS facultatif.
3. Patient concerné : ouvrir la notification ou Consultations → compte rendu.
4. Messages : ouvrir la conversation, envoyer une question. Le destinataire reçoit une notification. L'ouverture marque les messages reçus comme lus ; actualiser pour voir une nouvelle réponse.
5. Le médecin marque le rendez-vous terminé dans Appointments. Le patient peut alors donner une note de 1 à 5 et un commentaire, modifier ou supprimer son avis.
6. Avis : le médecin voit les avis reçus et leur moyenne. L'administrateur voit les avis et peut supprimer un commentaire depuis sa liste ; il n'accède pas aux comptes rendus ni aux messages via ce module.

## Modèles

- Consultation : relation unique avec Appointment, diagnostic, notes, lien_visio, dates.
- Message : consultation, auteur, contenu (4000 caractères maximum), date, lu.
- Avis : consultation unique, patient, medecin, note (contrainte SQL entre 1 et 5), commentaire, date.

## Autorisations et règles

Les participants sont déterminés par Appointment : aucune identité ni relation n'est fournie par les champs de formulaire. Les recherches de comptes rendus sont limitées à l'utilisateur connecté. Seul le médecin approuvé du rendez-vous peut créer, modifier ou supprimer une consultation. La suppression demande confirmation et entraîne la suppression des messages et de l'avis associés. Le rendez-vous est conservé. Inversement, sa suppression est bloquée tant qu'un compte rendu existe.

Un message ne peut être modifié ou supprimé que par son auteur. Les avis sont possibles uniquement après un rendez-vous terminé, avec un avis par consultation. Les notes du compte rendu sont visibles par le patient ; elles ne sont pas privées au médecin.

Les notifications passent par notifications.services.notify. Les liens de visio sont des URL HTTPS externes : pas de création automatique de salle ni d'appel intégré. Le bouton Imprimer / PDF utilise la boîte d'impression du navigateur. La messagerie fonctionne par envoi et rechargement de page, sans WebSocket.

## Interface

Les pages utilisent le tableau de bord existant, une feuille CSS dédiée et une présentation responsive. Recherche par nom, filtre de statut et pagination des comptes rendus ; pagination des avis ; statistiques calculées depuis la base. Les formulaires ont des labels, le focus clavier reste visible et toutes les mutations ont un jeton CSRF.

## Limites de déploiement

Module pédagogique local : il ne constitue pas à lui seul une certification de conformité pour un usage médical réel. La gestion des sauvegardes, de la conservation des dossiers et du déploiement reste celle du projet commun.

## Verification responsive (25 octobre 2026)

Les pages de liste, compte rendu, formulaire de consultation, conversation et avis ont ete controlees dans un navigateur avec des largeurs CSS mesurees de 320, 768 et 1280 pixels. La boite de reception a aussi ete controlee a 320 pixels. Aucun debordement horizontal du document n'a ete mesure apres correction. Le menu mobile a ete ouvert puis ferme avec son bouton ; le focus retourne au bouton d'ouverture.

Corrections : en-tete sur deux lignes, statistiques et formulaires en une colonne sur telephone, boutons tactiles de 44 pixels minimum, texte des champs a 16 pixels, cartes et textes longs contenus dans la largeur disponible, menu deroulant verticalement et bouton de fermeture. Les styles sont limites aux pages du module consultations. Verification par simulation de viewport, sans test sur un appareil physique. Ce controle ne remplace pas l'audit d'accessibilite Lighthouse/axe.

### Atelier dans la page de consultation

Le bouton de préparation déplie un bloc directement sous sa carte, sans fenêtre modale, changement d'URL ni blocage du défilement. La génération, l'animation, le résultat et la publication restent dans ce bloc. Les réponses JSON et les fragments HTML mettent à jour uniquement son contenu, en préservant la position de lecture. Le bouton Replier masque le bloc sans annuler une tâche déjà lancée. Une réouverture retrouve son état. Le mode page complète reste accessible par son URL pour compatibilité.

### Recherche dynamique

Les listes Consultations et Messages recherchent pendant la saisie (temporisation de 300 ms), sans bouton Filtrer et sans recharger la page. Les mots d’un nom complet sont combines. Les selecteurs appliquent immediatement les statuts ou le filtre non lu. La pagination est chargee dans la zone de resultats ; Effacer remet les criteres a zero. Les requetes precedentes sont annulees afin qu’une reponse ancienne ne remplace pas la recherche courante. Un echec conserve les cartes precedentes et affiche une indication. Les vues reutilisent exactement le filtrage des participants pour les fragments HTML et les pages completes.
