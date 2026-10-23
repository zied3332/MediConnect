from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Availability",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "weekday",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (0, "Monday"),
                            (1, "Tuesday"),
                            (2, "Wednesday"),
                            (3, "Thursday"),
                            (4, "Friday"),
                            (5, "Saturday"),
                            (6, "Sunday"),
                        ]
                    ),
                ),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("is_free", models.BooleanField(default=True)),
                (
                    "doctor",
                    models.ForeignKey(
                        limit_choices_to={"role": "doctor"},
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="availability_slots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("doctor", "weekday", "start_time"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("doctor", "weekday", "start_time", "end_time"),
                        name="unique_doctor_availability_slot",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(end_time__gt=models.F("start_time")),
                        name="availability_end_after_start",
                    ),
                ],
            },
        ),
    ]
