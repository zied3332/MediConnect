from django.db import models


class Specialty(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "core_specialty"
        ordering = ("name",)
        verbose_name_plural = "Specialties"
        managed = False

    def __str__(self):
        return self.name

