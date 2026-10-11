from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    # Authentication pages
    path("accounts/", include("accounts.urls")),

    # Homepage
    path("", include("core.urls")),
]