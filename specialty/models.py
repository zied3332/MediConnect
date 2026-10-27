from django.utils.translation import gettext_lazy as ui_gettext
from django.db import models


class Specialty(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "core_specialty"
        ordering = ("name",)
        verbose_name_plural = "Specialties"

    def __str__(self):
        return str(ui_gettext(self.name))
