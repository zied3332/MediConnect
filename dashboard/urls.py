from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # ── Admin ────────────────────────────────────────────
    path("admin/",                          views.admin_overview,      name="admin_overview"),
    path("admin/doctors/",                  views.admin_doctor_list,   name="admin_doctor_list"),
    path("admin/doctors/<int:pk>/",         views.admin_doctor_detail, name="admin_doctor_detail"),

    # ── Doctor ───────────────────────────────────────────
    path("doctor/",                         views.doctor_overview,     name="doctor_overview"),

    # ── Patient ──────────────────────────────────────────
    path("patient/",                        views.patient_overview,    name="patient_overview"),

    # Backward-compat
    path("",                                views.admin_overview,      name="overview"),
]
