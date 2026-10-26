
from django.urls import path

from . import views

app_name = "medical_records"

urlpatterns = [
    # ========================================================
    # Medical records
    # ========================================================

    path(
        "my/",
        views.my_medical_record,
        name="my_record",
    ),

    path(
        "patients/<int:patient_id>/",
        views.patient_medical_record,
        name="patient_record",
    ),

    # ========================================================
    # Prescriptions
    # ========================================================

    path(
        "prescriptions/",
        views.prescription_list,
        name="prescription_list",
    ),

    path(
        "consultations/<int:consultation_id>/prescriptions/new/",
        views.prescription_create,
        name="prescription_create",
    ),

    path(
        "prescriptions/<int:pk>/",
        views.prescription_detail,
        name="prescription_detail",
    ),

    path(
        "prescriptions/<int:pk>/edit/",
        views.prescription_edit,
        name="prescription_edit",
    ),

    path(
        "prescriptions/<int:pk>/delete/",
        views.prescription_delete,
        name="prescription_delete",
    ),

    # ========================================================
    # Medical examinations
    # ========================================================

    path(
        "patients/<int:patient_id>/examinations/",
        views.examination_list,
        name="examination_list",
    ),

    path(
        "examinations/upload/",
        views.examination_upload,
        name="examination_upload",
    ),

    path(
        "examinations/<int:pk>/download/",
        views.examination_download,
        name="examination_download",
    ),
]
