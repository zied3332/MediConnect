from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("admin/",   views.admin_overview,   name="admin_overview"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/users/<int:user_id>/role/", views.update_user_role, name="update_user_role"),
    path("admin/specialties/", views.admin_specialties, name="admin_specialties"),
    path("admin/specialties/all/", views.specialty_list, name="specialty_list"),
    path("admin/specialties/<int:specialty_id>/edit/", views.edit_specialty, name="edit_specialty"),
    path("admin/specialties/<int:specialty_id>/delete/", views.delete_specialty, name="delete_specialty"),
    path("admin/specialties/doctor/<int:user_id>/", views.update_doctor_specialty, name="update_doctor_specialty"),
    path("admin/availability/", views.admin_availability, name="admin_availability"),
    path("admin/availability/<int:slot_id>/delete/", views.delete_availability, name="delete_availability"),
    path("doctor/availability/", views.doctor_availability, name="doctor_availability"),
    path("doctor/availability/<int:slot_id>/edit/", views.edit_doctor_availability, name="edit_doctor_availability"),
    path("doctor/availability/<int:slot_id>/delete/", views.delete_doctor_availability, name="delete_doctor_availability"),
    path("doctor/availability/<int:slot_id>/toggle/", views.toggle_doctor_availability, name="toggle_doctor_availability"),
    path("doctor/",  views.doctor_overview,  name="doctor_overview"),
    path("patient/", views.patient_overview, name="patient_overview"),
    # Backward-compat: /dashboard/ → admin overview
    path("",         views.admin_overview,   name="overview"),
]
