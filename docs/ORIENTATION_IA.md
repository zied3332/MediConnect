# Orientation IA — démonstration et justification technique

## Besoin réel

Le patient décrit son état dans un seul paragraphe, en précisant librement durée et impact s'il le souhaite. Une API Anthropic propose une spécialité parmi celles réellement associées à des médecins actifs et approuvés. La réservation conserve ses propres contrôles et disponibilités. Aucun diagnostic, traitement ou triage clinique certifié n'est fourni. La fiche patient après consultation reste indépendante.

L'API peut produire des phrases supplémentaires malgré le prompt. L'application n'affiche donc pas sa prose médicale libre : elle conserve sa décision d'orientation, affiche une explication fixe de cette décision et reprend les mots originaux du patient. Cela évite de présenter une reformulation infidèle ou une suggestion d'examens. Le modèle d'orientation ne remplace pas la fiche générative après consultation, qui conserve sa validation médicale.

## Démarrer sur cet ordinateur Windows

La migration `consultations.0004_aiintakesession` doit être appliquée :

```powershell
python manage.py migrate
```

Dans un premier terminal, depuis le projet avec le venv activé :

```powershell
python -m celery -A consultations.intake_worker:app worker --pool=solo --concurrency=1 --loglevel=WARNING --without-gossip --without-mingle --without-heartbeat
```

Dans un deuxième terminal :

```powershell
python manage.py runserver
```

Connexion patiente : `marie.dupont@mediconnect.demo`, mot de passe de démonstration `Demo1234!`.
Menu **Orientation IA**, ou `/consultations/orientation/`.

Exemple fictif : « Mon médecin m’a demandé un suivi dermatologique de routine, sans symptôme nouveau. » L'accord d'envoi est associé au bouton « Accepter et préparer » ; pas de liste déroulante ni de case supplémentaire. Le chargement, le résultat et les médecins restent sur la même page. Le lien ouvre les vrais créneaux du médecin. Le bouton d'effacement supprime la session et ses réponses en base.

Si l'API signale une urgence possible dans le paragraphe, aucun médecin n'est proposé et le message invite à contacter une aide humaine immédiate. Le questionnaire de sécurité structuré a été retiré à la demande de l'utilisateur : ce mécanisme dépend désormais de l'analyse du texte par le modèle. Il ne détecte pas toutes les urgences et ne permet jamais d'en exclure une. Le message d'urgence général reste visible avant la saisie.

## Asynchronisme : dire exactement ce qui est démontré

Le worker d'orientation est séparé du serveur web, même si les autres tâches du projet utilisent `CELERY_TASK_ALWAYS_EAGER=True`.

Par défaut, il utilise le Redis configuré pour Celery. Ici Docker/WSL ne démarrait pas : `.env` configure `ORIENTATION_BROKER_URL=filesystem://` pour une file locale Kombu/Celery. C'est du vrai traitement dans un processus séparé, **pas une démonstration Redis**. Seul l'UUID de la session passe dans la file ; le worker lit les réponses dans PostgreSQL. Le répertoire `.orientation-queue/` est ignoré par Git. Ce transport est destiné à la démonstration locale, sans disponibilité multi-serveur ni garantie de production.

Pour Redis opérationnel, mettre `ORIENTATION_BROKER_URL=redis://localhost:6379/0` dans `.env`, puis redémarrer serveur et worker. Ne pas lancer deux workers différents pour la même démonstration.

Source du transport local : https://docs.celeryq.dev/projects/kombu/en/v5.5.0/reference/kombu.transport.filesystem.html

## Fichiers à expliquer au jury

- `models.py` : `AIIntakeSession` appartient à un patient (ForeignKey), UUID, réponses JSON, résultat, état, consentement et durée. Pas de seconde table de chat : questionnaire borné, pas de conversation médicale libre illimitée.
- `intake_views.py` : formulaire, contrôle patient, création sans quota de demandes, état privé et suppression POST.
- `intake_worker.py` : application Celery indépendante, exécution eager désactivée.
- `intake_tasks.py` : lit la session, appelle le service, persiste ready/urgent/failed ; ne journalise pas de texte médical.
- `intake_ai.py` : appel HTTPS, délai 35 s, catalogue fermé, validation JSON stricte, erreurs assainies. Les garde-fous structurels ne prouvent pas la justesse médicale.
- `intake.html` et `intake.js` : formulaire labellisé, consentement, fetch, animation à mouvement réduit, chronomètre réel, polling, rendu avec textContent (pas de HTML produit par le modèle).

Trajet : navigateur → POST start → PostgreSQL + file Celery → HTTP 202 → worker → API Anthropic → PostgreSQL → GET status → résultat dans la page.

## Évaluation reproductible

```powershell
python manage.py test consultations
python manage.py evaluate_orientation --live
```

La seconde commande effectue **5 appels payants** contenant uniquement les cas fictifs intégrés au code, sans lire les dossiers des patients. Résultats : `docs/orientation-evaluation.json`. Elle mesure format valide, correspondance à la spécialité attendue, moyenne, médiane et P95 au rang le plus proche. Le P95 de cinq cas est essentiellement le maximum, pas une estimation robuste de charge.

`docs/orientation-async-smoke.json` contient un essai réel séparé : temps de retour HTTP, statut final et durée API. Le compte temporaire et sa session ont été supprimés après l'essai.

### Analyse qualitative à compléter avec l'étudiant / encadrant

Chaque cas comporte trois critères notés 0, 1 ou 2 : fidélité au texte, clarté et absence de diagnostic/prescription. 0 = échec, 1 = réserve, 2 = satisfaisant. Les champs restent vides tant qu'aucun évaluateur humain identifié n'a noté les sorties. Ne pas les présenter comme validés médicalement. Revoir notamment toute transformation de « demandé » en « prescrit », et toute conclusion injustifiée de stabilité ou d'absence d'urgence.

Les intentions de ce petit jeu sont explicites : bilan général, suivi cardiologique, suivi dermatologique, manque d'informations et instruction malveillante. Les correspondances attendues sont des références pédagogiques, pas des labels de diagnostic validés par un expert. Étendre le jeu avec un professionnel avant tout usage réel. Aucun 4/4 n'est garanti.

## Confidentialité et exploitation

La clé reste dans `.env` ; remplacer toute clé partagée dans une conversation. Consentement avant envoi, pas de transmission automatique du nom, e-mail, messages ou dossier médical. Le texte libre peut contenir des identifiants saisis : utiliser des données fictives pour la soutenance. Seul le propriétaire accède à sa session. Le contenu est conservé en base jusqu'à son effacement ou la purge :

```powershell
python manage.py purge_ai_intakes
```

Cette commande supprime les sessions de plus de 7 jours ; elle doit être exécutée régulièrement, elle n'est pas planifiée automatiquement. Le stockage de santé réel, sa conservation et les sauvegardes nécessitent le travail de conformité et d'exploitation du projet.

## Limite existante du projet commun

`makemigrations --check --dry-run` signale un décalage préexistant : le champ `User.main_specialty` pointe vers `core.Specialty` dans le modèle, mais la migration accounts.0006 vise l'alias `specialty.Specialty` (même table physique). L'orientation utilise le modèle courant, comme la réservation, pour ne pas changer les relations de l'équipe. Cette incohérence doit être résolue avec le responsable du module spécialités, puis testée sur les autres applications.
