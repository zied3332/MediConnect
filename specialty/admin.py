from django.contrib import admin

from .models import Specialty


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")

