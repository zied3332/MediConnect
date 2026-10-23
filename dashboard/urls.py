from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("admin/",   views.admin_overview,   name="admin_overview"),
    path("admin/users/", views.admin_users, name="admin_users"),
    path("admin/users/<int:user_id>/role/", views.update_user_role, name="update_user_role"),
    path("doctor/",  views.doctor_overview,  name="doctor_overview"),
    path("patient/", views.patient_overview, name="patient_overview"),
    # Backward-compat: /dashboard/ → admin overview
    path("",         views.admin_overview,   name="overview"),
]
