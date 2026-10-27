
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # ── Admin ─────────────────────────────────────────────
    path("admin/", views.admin_overview, name="admin_overview"),
    path("admin/doctors/", views.admin_doctor_list, name="admin_doctor_list"),
    path("admin/doctors/<int:pk>/", views.admin_doctor_detail, name="admin_doctor_detail"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/users/<int:user_id>/role/", views.update_user_role, name="update_user_role"),

    # ── Doctor ────────────────────────────────────────────
    path("doctor/", views.doctor_overview, name="doctor_overview"),
    path("doctor/patients/", views.doctor_patients, name="doctor_patients"),

    # ── Patient ───────────────────────────────────────────
    path("patient/", views.patient_overview, name="patient_overview"),
    path("patient/doctors/", views.patient_doctors, name="patient_doctors"),

    # ── Profile (all roles) ───────────────────────────────
    path("profile/", views.profile_view, name="profile"),

    # ── Backward compatibility ────────────────────────────
    path("", views.admin_overview, name="overview"),
]
