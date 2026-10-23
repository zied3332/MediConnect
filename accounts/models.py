import os

from django.contrib.auth.models import AbstractUser
from django.db import models


def doctor_document_upload_path(instance, filename):
    """Store documents under media/doctors/<user_id>/<filename>."""
    return os.path.join("doctors", str(instance.user.id), filename)


class User(AbstractUser):
    """
    Custom MediConnect user.

    Extends Django's AbstractUser. The `role` field drives dashboard routing.
    Doctors also have a linked DoctorProfile that tracks their verification
    status and uploaded documents.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"

    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    # Doctors are created with is_active=False until email is confirmed.
    # Patients are active immediately.

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}> [{self.role}]"

    @property
    def dashboard_url(self):
        """Return the landing URL for the user's role."""
        from django.urls import reverse

        mapping = {
            self.Role.ADMIN: "dashboard:admin_overview",
            self.Role.DOCTOR: "dashboard:doctor_overview",
            self.Role.PATIENT: "dashboard:patient_overview",
        }
        return reverse(mapping[self.role])


class DoctorProfile(models.Model):
    """
    Extended profile for doctors.

    Tracks the verification workflow from registration through
    approval or rejection.
    """

    class Status(models.TextChoices):
        PENDING_DOCUMENTS = "pending_documents", "Pending documents"
        PENDING_REVIEW    = "pending_review",    "Pending review"
        NEEDS_MORE_INFO   = "needs_more_info",   "Needs more info"
        APPROVED          = "approved",          "Approved"
        REJECTED          = "rejected",          "Rejected"

    SPECIALTY_CHOICES = [
        ("general_medicine",   "General Medicine"),
        ("cardiology",         "Cardiology"),
        ("dermatology",        "Dermatology"),
        ("pediatrics",         "Pediatrics"),
        ("gynecology",         "Gynecology & Obstetrics"),
        ("neurology",          "Neurology"),
        ("orthopedics",        "Orthopedics"),
        ("psychiatry",         "Psychiatry"),
        ("ophthalmology",      "Ophthalmology"),
        ("ent",                "ENT (Ear, Nose & Throat)"),
        ("dentistry",          "Dentistry"),
        ("radiology",          "Radiology"),
        ("oncology",           "Oncology"),
        ("endocrinology",      "Endocrinology"),
        ("urology",            "Urology"),
        ("nephrology",         "Nephrology"),
        ("gastroenterology",   "Gastroenterology"),
        ("pulmonology",        "Pulmonology"),
        ("rheumatology",       "Rheumatology"),
        ("other",              "Other"),
    ]

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )

    specialty = models.CharField(max_length=50, choices=SPECIALTY_CHOICES)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_DOCUMENTS,
    )

    # ── Documents ────────────────────────────────────────────────────────
    # medical_license: medical license or registration number document
    medical_license = models.FileField(
        upload_to=doctor_document_upload_path,
        null=True, blank=True,
        help_text="Medical license or professional registration number.",
    )

    # diploma: university diploma or specialty certificate
    diploma = models.FileField(
        upload_to=doctor_document_upload_path,
        null=True, blank=True,
        help_text="Diploma or specialty certificate.",
    )

    # national_id: national ID card or passport
    national_id = models.FileField(
        upload_to=doctor_document_upload_path,
        null=True, blank=True,
        help_text="National ID card or passport.",
    )

    # selfie_with_id: optional photo of doctor holding their ID
    selfie_with_id = models.ImageField(
        upload_to=doctor_document_upload_path,
        null=True, blank=True,
        help_text="Optional selfie holding the ID — proves it's really you.",
    )

    # ── Review metadata ──────────────────────────────────────────────────
    rejection_reason = models.TextField(
        blank=True,
        help_text="Filled by an admin when the application is rejected.",
    )

    reviewer_note = models.TextField(
        blank=True,
        help_text="Message shown to the doctor when more info is needed.",
    )

    submitted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When documents were submitted for review.",
    )

    reviewed_at = models.DateTimeField(
        null=True, blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Doctor profile"
        verbose_name_plural = "Doctor profiles"

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.get_status_display()}"

    @property
    def can_access_dashboard(self):
        """True only when fully approved."""
        return self.status == self.Status.APPROVED

    @property
    def documents_complete(self):
        """True when all three mandatory documents are uploaded."""
        return bool(self.medical_license and self.diploma and self.national_id)
