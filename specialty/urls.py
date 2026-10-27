from django.urls import path

from . import views

app_name = "specialty"

urlpatterns = [
    path("admin/specialties/", views.admin_specialties, name="admin_specialties"),
    path("admin/specialties/all/", views.specialty_list, name="specialty_list"),
    path(
        "admin/specialties/<int:specialty_id>/edit/",
        views.edit_specialty,
        name="edit_specialty",
    ),
    path(
        "admin/specialties/<int:specialty_id>/delete/",
        views.delete_specialty,
        name="delete_specialty",
    ),
    path(
        "admin/specialties/doctor/<int:user_id>/",
        views.update_doctor_specialty,
        name="update_doctor_specialty",
    ),
]
