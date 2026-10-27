# Copilote de rédaction de consultation

Ce parcours remplace la fiche patient simplifiée dans l'interface. Depuis un compte médecin approuvé : **Consultations → compte rendu → Ouvrir le copilote**, ou ouvrir le formulaire de rédaction depuis un rendez-vous confirmé/terminé. L'orientation IA avant rendez-vous reste indépendante.

1. Saisir des notes de 20 à 8 000 caractères et accepter leur envoi à Anthropic.
2. Claude classe des extraits dans quatre rubriques : motif, observations, diagnostic et suivi.
3. Le serveur vérifie le JSON, les citations et les unités complètes de texte ; un résultat non conforme est refusé.
4. Le médecin compare les extraits avec les notes, corrige les champs et confirme sa relecture.
5. **Appliquer** remplit le formulaire, sans enregistrer. **Enregistrer le compte rendu** conserve la validation Django et rend le compte rendu accessible au patient.

Les rubriques absentes restent vides. Le diagnostic obligatoire doit être explicitement complété par le médecin. L'IA ne déduit pas de diagnostic et ne propose ni prescription ni traitement. La validation des citations réduit le risque d'ajout, sans garantir la pertinence du classement : la relecture médicale reste nécessaire.

La clé reste dans les variables d'environnement. L'appel serveur utilise TLS, un délai de 35 secondes et des erreurs sans contenu de réponse sensible. Seules les notes saisies sont envoyées ; aucun dossier, nom ou e-mail n'est ajouté automatiquement. Les notes ne doivent donc pas contenir d'identifiants inutiles.

Les anciennes données `PatientBrief` sont conservées. L'ancienne URL `/consultations/<id>/fiche/` redirige désormais le médecin vers le formulaire et le patient vers son compte rendu. Les API historiques sont maintenues pour compatibilité, sans lien dans le nouveau parcours.

## Démonstration fictive

> Motif : consultation de suivi. Observations : le patient pose des questions sur le précédent compte rendu. Diagnostic : aucun nouveau diagnostic établi. Suivi : préparer les questions pour le prochain échange. Aucun traitement supplémentaire prescrit.

Fichiers principaux : `consultations/copilot.py`, `templates/consultations/copilot.html`, `static/js/copilot.js`, `static/css/dashboard/copilot.css`. Tests : `python manage.py test consultations.test_copilot --keepdb --noinput`.
