
from django.contrib import admin

from .models import DossierMedical, Ordonnance, Examen


@admin.register(DossierMedical)
class DossierMedicalAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient",
        "created_at",
        "updated_at",
    )

    list_display_links = ("id", "patient")

    search_fields = (
        "patient__email",
        "patient__first_name",
        "patient__last_name",
        "antecedents",
        "allergies",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_select_related = ("patient",)

    ordering = ("-created_at",)


@admin.register(Ordonnance)
class OrdonnanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "consultation",
        "date",
        "created_at",
    )

    list_filter = ("date",)

    search_fields = (
        "medicaments",
        "instructions",
    )

    readonly_fields = ("created_at",)

    list_select_related = ("consultation",)

    ordering = ("-date",)


@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "titre",
        "dossier",
        "date",
        "created_at",
    )

    list_filter = ("date",)

    search_fields = (
        "titre",
        "dossier__patient__email",
    )

    readonly_fields = ("created_at",)

    list_select_related = ("dossier",)

    ordering = ("-date",)
