from django.urls import path

from . import views

app_name = "availability"

urlpatterns = [
    path("admin/availability/", views.admin_availability, name="admin_availability"),
    path(
        "admin/availability/<int:slot_id>/delete/",
        views.delete_availability,
        name="delete_availability",
    ),
    path("doctor/availability/", views.doctor_availability, name="doctor_availability"),
    path(
        "doctor/availability/<int:slot_id>/edit/",
        views.edit_doctor_availability,
        name="edit_doctor_availability",
    ),
    path(
        "doctor/availability/<int:slot_id>/delete/",
        views.delete_doctor_availability,
        name="delete_doctor_availability",
    ),
    path(
        "doctor/availability/<int:slot_id>/toggle/",
        views.toggle_doctor_availability,
        name="toggle_doctor_availability",
    ),
]

