from django.urls import path

from . import views
from .preferences import preferences_page

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("preferences/", preferences_page, name="preferences"),
]
