from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # ── Shared ────────────────────────────────────────
    path("login/",  views.login_page,   name="login"),
    path("signup/", views.signup_page,  name="signup"),
    path("logout/", views.logout_view,  name="logout"),

    # ── Doctor registration flow ──────────────────────
    path(
        "doctor/signup/",
        views.doctor_signup,
        name="doctor_signup",
    ),
    path(
        "doctor/confirm-email/<uidb64>/<token>/",
        views.doctor_confirm_email,
        name="doctor_confirm_email",
    ),
    path(
        "doctor/upload-documents/<int:pk>/",
        views.doctor_upload_docs,
        name="doctor_upload_docs",
    ),
    path(
        "doctor/status/",
        views.doctor_status,
        name="doctor_status",
    ),
]
