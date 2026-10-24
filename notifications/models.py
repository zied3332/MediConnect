from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app message shown to one user (bell in the dashboard topbar).

    Never create these directly: use notifications.services.notify().
    """

    class Type(models.TextChoices):
        APPOINTMENT = "appointment", "Appointment"
        REMINDER = "reminder", "Reminder"
        SYSTEM = "system", "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=500)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    # Internal path (e.g. /appointments/12/) opened when the notification is read.
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("user", "is_read"), name="notif_user_read_idx"),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.message[:50]}"
