from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom MediConnect user.

    Extends Django's AbstractUser so all built-in fields
    (username, email, first_name, last_name, password…) are
    preserved. A single `role` field drives dashboard routing.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"

    email = models.EmailField(unique=True)

    main_specialty = models.ForeignKey(
        "core.Specialty",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="doctors",
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
    )

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
