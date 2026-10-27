from django.utils.translation import gettext_lazy as ui_gettext
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

# Longest appointment we accept; used to bound overlap queries.
MAX_DURATION_MINUTES = 240

# Risk thresholds shown to doctors (Low < 0.3, Medium < 0.6, High otherwise).
RISK_MEDIUM_THRESHOLD = 0.3
RISK_HIGH_THRESHOLD = 0.6


class Appointment(models.Model):
    """A consultation booked by a patient with an approved doctor."""

    class Mode(models.TextChoices):
        CABINET = "cabinet", ui_gettext("In-office")
        VISIO = "visio", ui_gettext("Video call")

    class Status(models.TextChoices):
        PENDING = "pending", ui_gettext("Pending")
        CONFIRMED = "confirmed", ui_gettext("Confirmed")
        REJECTED = "rejected", ui_gettext("Rejected")
        CANCELLED = "cancelled", ui_gettext("Cancelled")
        COMPLETED = "completed", ui_gettext("Completed")
        NO_SHOW = "no_show", ui_gettext("No-show")

    class RiskStatus(models.TextChoices):
        PENDING = "pending", ui_gettext("Computing")
        READY = "ready", ui_gettext("Ready")
        FAILED = "failed", ui_gettext("Failed")

    ACTIVE_STATUSES = (Status.PENDING, Status.CONFIRMED)

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
        limit_choices_to={"role": "patient"},
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_appointments",
        limit_choices_to={"role": "doctor"},
    )
    start = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(MAX_DURATION_MINUTES)],
    )
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.CABINET)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reason = models.TextField(help_text=ui_gettext("Why the patient wants to see the doctor."))
    # Optional message from the doctor when rejecting.
    status_note = models.TextField(blank=True)

    # ── AI no-show risk (computed asynchronously by Celery) ─────────────
    no_show_risk = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    risk_status = models.CharField(
        max_length=10, choices=RiskStatus.choices, default=RiskStatus.PENDING
    )

    # ── Reminders ───────────────────────────────────────────────────────
    reminder_sent = models.BooleanField(default=False)
    early_reminder_sent = models.BooleanField(
        default=False, help_text=ui_gettext("Extra 48h reminder sent because risk is high.")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("start",)
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "start"),
                condition=models.Q(status__in=("pending", "confirmed")),
                name="unique_active_appointment_per_doctor_start",
            ),
            models.CheckConstraint(
                condition=models.Q(no_show_risk__isnull=True)
                | models.Q(no_show_risk__gte=0, no_show_risk__lte=1),
                name="appointment_risk_between_0_and_1",
            ),
        ]
        indexes = [
            models.Index(fields=("doctor", "start"), name="appt_doctor_start_idx"),
            models.Index(fields=("patient", "start"), name="appt_patient_start_idx"),
            models.Index(fields=("status", "start"), name="appt_status_start_idx"),
        ]

    def __str__(self):
        return (
            f"{self.patient.get_full_name() or self.patient.email} with "
            f"Dr. {self.doctor.get_full_name() or self.doctor.email} — "
            f"{timezone.localtime(self.start):%Y-%m-%d %H:%M} ({self.status})"
        )

    def get_absolute_url(self):
        return reverse("appointments:detail", args=[self.pk])

    # ── Convenience properties ──────────────────────────────────────────
    @property
    def end(self):
        return self.start + timedelta(minutes=self.duration_minutes)

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def is_upcoming(self):
        return self.is_active and self.start > timezone.now()

    @property
    def can_be_changed_by_patient(self):
        """Cancel / reschedule allowed only more than 24h before the start."""
        return self.is_active and self.start - timezone.now() > timedelta(hours=24)

    @property
    def risk_level(self):
        if self.no_show_risk is None:
            return None
        if self.no_show_risk < RISK_MEDIUM_THRESHOLD:
            return "low"
        if self.no_show_risk < RISK_HIGH_THRESHOLD:
            return "medium"
        return "high"

    @property
    def risk_percent(self):
        if self.no_show_risk is None:
            return None
        return round(self.no_show_risk * 100)

    # ── Validation ──────────────────────────────────────────────────────
    def clean(self):
        super().clean()
        # Booking rules only apply to active appointments; historical ones
        # (completed, cancelled...) are kept as they are.
        if not self.start or not self.is_active:
            return
        if not self.patient_id or not self.doctor_id:
            return

        errors = []
        if self.patient.role != "patient":
            errors.append("Only patients can book appointments.")
        if self.doctor.role != "doctor":
            errors.append("The selected user is not a doctor.")
        if self.start <= timezone.now():
            errors.append("The appointment must be in the future.")
        if not _doctor_is_approved(self.doctor):
            errors.append("This doctor is not approved yet.")
        if errors:
            raise ValidationError(errors)

        if not self._inside_availability():
            raise ValidationError(
                ui_gettext("This time is outside the doctor's availability.")
            )
        if self._overlapping(doctor=self.doctor).exists():
            raise ValidationError(ui_gettext("The doctor already has an appointment at this time."))
        if self._overlapping(patient=self.patient).exists():
            raise ValidationError(ui_gettext("You already have an appointment at this time."))

    def _inside_availability(self):
        from availability.models import Availability

        start = timezone.localtime(self.start)
        end = timezone.localtime(self.end)
        if start.date() != end.date():
            return False
        return Availability.objects.filter(
            doctor_id=self.doctor_id,
            weekday=start.weekday(),
            is_free=True,
            start_time__lte=start.time(),
            end_time__gte=end.time(),
        ).exists()

    def _overlapping(self, **owner):
        """Active appointments of the same doctor/patient that overlap this one."""
        candidates = Appointment.objects.filter(
            status__in=self.ACTIVE_STATUSES,
            start__lt=self.end,
            start__gt=self.start - timedelta(minutes=MAX_DURATION_MINUTES),
            **owner,
        ).exclude(pk=self.pk)
        overlapping_ids = [a.pk for a in candidates if a.end > self.start]
        return Appointment.objects.filter(pk__in=overlapping_ids)


def _doctor_is_approved(doctor):
    from accounts.models import DoctorProfile

    try:
        return doctor.doctor_profile.status == DoctorProfile.Status.APPROVED
    except DoctorProfile.DoesNotExist:
        return False
