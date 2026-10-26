
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentication and user accounts
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),  # Google OAuth callbacks

    # User dashboards and notifications
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),

    # Appointments and consultations
    path("appointments/", include("appointments.urls")),
    path("consultations/", include("consultations.urls")),

    # Medical Records — Module 4
    path("medical-records/", include("medical_records.urls")),

    # Public website (keep this route last)
    path("", include("core.urls")),
]

# Serve uploaded files during development.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
