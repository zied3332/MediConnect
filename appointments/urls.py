from django.urls import path

from . import views

app_name = "appointments"

urlpatterns = [
    # ── Patient ──────────────────────────────────────────
    path("",                              views.my_appointments,        name="my_list"),
    path("book/",                         views.book_appointment,       name="book"),
    path("book/doctor/<int:doctor_id>/",  views.book_with_doctor,       name="book_slot"),
    path("<int:pk>/",                     views.appointment_detail,     name="detail"),
    path("<int:pk>/reschedule/",          views.reschedule_appointment, name="reschedule"),
    path("<int:pk>/cancel/",              views.cancel_appointment,     name="cancel"),

    # ── Doctor ───────────────────────────────────────────
    path("doctor/",                        views.doctor_appointments, name="doctor_list"),
    path("doctor/<int:pk>/<slug:action>/", views.doctor_action,       name="doctor_action"),

    # ── Admin ────────────────────────────────────────────
    path("admin/",                  views.admin_appointments,       name="admin_list"),
    path("admin/<int:pk>/delete/",  views.admin_delete_appointment, name="admin_delete"),
    path("admin/ai-model/",         views.admin_ai_model,           name="admin_ai_model"),
]
