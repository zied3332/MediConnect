from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),   # Google OAuth callbacks
    path("dashboard/", include("dashboard.urls")),
    path("notifications/", include("notifications.urls")),
    path("appointments/", include("appointments.urls")),
    path("", include("core.urls")),
]

# Serve uploaded files during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
