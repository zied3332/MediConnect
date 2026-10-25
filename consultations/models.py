from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.db import models
import uuid

from appointments.models import Appointment


class Consultation(models.Model):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.PROTECT, related_name="consultation",
        verbose_name="rendez-vous",
    )
    diagnostic = models.TextField()
    notes = models.TextField(blank=True)
    lien_visio = models.URLField(blank=True, validators=[URLValidator(schemes=["https"])])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-appointment__start",)

    def clean(self):
        super().clean()
        if self.appointment_id and self.appointment.status not in (
            Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED,
        ):
            raise ValidationError("Le rendez-vous doit être confirmé ou terminé.")

    def __str__(self):
        return f"Consultation du rendez-vous {self.appointment_id}"


class Message(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name="messages")
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    contenu = models.TextField(max_length=4000)
    date = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        ordering = ("date", "pk")

    def clean(self):
        if self.consultation_id and self.auteur_id:
            appointment = self.consultation.appointment
            if self.auteur_id not in (appointment.patient_id, appointment.doctor_id):
                raise ValidationError("Vous ne participez pas à cette consultation.")
        if not self.contenu.strip():
            raise ValidationError({"contenu": "Écrivez un message avant de l'envoyer."})


class Avis(models.Model):
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name="avis")
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="avis_rediges")
    medecin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="avis_recus")
    note = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField(max_length=2000)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-date",)
        constraints = [models.CheckConstraint(condition=models.Q(note__gte=1, note__lte=5), name="avis_note_1_5")]

    def clean(self):
        if self.consultation_id:
            appointment = self.consultation.appointment
            if appointment.status != Appointment.Status.COMPLETED:
                raise ValidationError("Vous pourrez laisser un avis après la fin du rendez-vous.")
            if self.patient_id != appointment.patient_id or self.medecin_id != appointment.doctor_id:
                raise ValidationError("L'avis doit concerner le patient et le médecin de cette consultation.")


class PatientBrief(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En préparation"
        READY = "ready", "À vérifier"
        FAILED = "failed", "Indisponible"
        PUBLISHED = "published", "Validé par le médecin"

    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name="patient_brief")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    generation_id = models.UUIDField(default=uuid.uuid4)
    source_hash = models.CharField(max_length=64)
    cards = models.JSONField(default=list)
    approved_cards = models.JSONField(default=list)
    error_code = models.CharField(max_length=30, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
