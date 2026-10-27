from django.utils.translation import gettext_lazy as ui_gettext

from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from .storage import private_medical_storage

class DossierMedical(models.Model):
    """Medical record belonging to one patient."""

    patient = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dossier_medical",
    )

    antecedents = models.TextField(
        blank=True,
        verbose_name=ui_gettext("Antécédents médicaux"),
    )

    allergies = models.TextField(
        blank=True,
        verbose_name=ui_gettext("Allergies"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dossier médical"
        verbose_name_plural = "Dossiers médicaux"

    def clean(self):
        super().clean()

        if self.patient_id and self.patient.role != "patient":
            raise ValidationError({
                "patient": "Le dossier doit appartenir à un patient."
            })

    def __str__(self):
        return f"Dossier médical de {self.patient.email}"


class Ordonnance(models.Model):
    """Prescription issued during a consultation."""

    consultation = models.ForeignKey(
        "consultations.Consultation",
        on_delete=models.PROTECT,
        related_name="ordonnances",
    )

    date = models.DateField(
        default=timezone.localdate,
    )

    medicaments = models.TextField(
        verbose_name=ui_gettext("Médicaments"),
    )

    instructions = models.TextField(
        blank=True,
        verbose_name=ui_gettext("Instructions"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ordonnance"
        verbose_name_plural = "Ordonnances"
        ordering = ["-date", "-id"]

    def clean(self):
        super().clean()

        if not self.medicaments.strip():
            raise ValidationError({
                "medicaments": "Indiquez au moins un médicament."
            })

    def __str__(self):
        return f"Ordonnance #{self.pk}"


def examen_upload_path(instance, filename):
    """Generate an unpredictable storage filename."""
    extension = Path(filename).suffix.lower()
    return (
        f"medical_records/{instance.dossier.patient_id}/exams/"
        f"{uuid4().hex}{extension}"
    )


class Examen(models.Model):
    """Medical examination associated with a patient's record."""

    dossier = models.ForeignKey(
        DossierMedical,
        on_delete=models.PROTECT,
        related_name="examens",
    )

    titre = models.CharField(
        max_length=200,
        verbose_name=ui_gettext("Titre"),
    )

    fichier = models.FileField(
          upload_to=examen_upload_path,
          storage=private_medical_storage,
          verbose_name=ui_gettext("Fichier"),
    )

    date = models.DateField(
        default=timezone.localdate,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Examen médical"
        verbose_name_plural = "Examens médicaux"
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.titre
