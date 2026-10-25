from django.urls import path
from . import views
from . import brief_views

app_name = "consultations"
urlpatterns = [
    path("<int:pk>/fiche/", brief_views.brief_page, name="brief"),
    path("<int:pk>/fiche/generate/", brief_views.brief_generate, name="brief_generate"),
    path("<int:pk>/fiche/status/", brief_views.brief_status, name="brief_status"),
    path("<int:pk>/fiche/publish/", brief_views.brief_publish, name="brief_publish"),
    path("", views.consultation_list, name="list"),
    path("messages/", views.inbox, name="inbox"),
    path("messages/<int:pk>/edit/", views.message_edit, name="message_edit"),
    path("messages/<int:pk>/delete/", views.message_delete, name="message_delete"),
    path("avis/", views.reviews, name="reviews"),
    path("avis/<int:pk>/delete/", views.review_delete, name="review_delete"),
    path("appointment/<int:appointment_id>/edit/", views.edit, name="edit"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/messages/", views.conversation, name="conversation"),
    path("<int:pk>/avis/", views.review_edit, name="review_edit"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
