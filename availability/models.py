from django.utils.translation import gettext_lazy as ui_gettext
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Availability(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, ui_gettext("Monday")
        TUESDAY = 1, ui_gettext("Tuesday")
        WEDNESDAY = 2, ui_gettext("Wednesday")
        THURSDAY = 3, ui_gettext("Thursday")
        FRIDAY = 4, ui_gettext("Friday")
        SATURDAY = 5, ui_gettext("Saturday")
        SUNDAY = 6, ui_gettext("Sunday")

    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availability_slots",
        limit_choices_to={"role": "doctor"},
    )
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_free = models.BooleanField(default=True)

    class Meta:
        db_table = "core_availability"
        managed = False
        ordering = ("doctor", "weekday", "start_time")
        constraints = [
            models.UniqueConstraint(
                fields=("doctor", "weekday", "start_time", "end_time"),
                name="unique_doctor_availability_slot",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="availability_end_after_start",
            ),
        ]

    def clean(self):
        if not self.start_time or not self.end_time:
            return
        if self.end_time <= self.start_time:
            raise ValidationError(ui_gettext("End time must be after start time."))

        overlapping = Availability.objects.filter(
            doctor=self.doctor,
            weekday=self.weekday,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        if overlapping.exists():
            raise ValidationError(
                ui_gettext("This availability overlaps another slot for the same doctor.")
            )

    def __str__(self):
        return (
            f"{self.doctor.get_full_name()} - "
            f"{self.get_weekday_display()} {self.start_time:%H:%M}-{self.end_time:%H:%M}"
        )
