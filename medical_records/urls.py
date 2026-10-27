
from django.urls import path

from . import views, admin_views


app_name = "medical_records"


urlpatterns = [

    # ========================================================
    # Medical Records — Patient / Doctor
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
    # Prescriptions — Patient / Doctor
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
    # Medical Examinations — Patient / Doctor
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

    # ========================================================
    # Website Admin — Medical Records CRUD (Phase 1)
    # ========================================================

    path(
        "management/records/",
        admin_views.admin_record_list,
        name="admin_record_list",
    ),

    path(
        "management/records/new/",
        admin_views.admin_record_create,
        name="admin_record_create",
    ),

    path(
        "management/records/<int:pk>/",
        admin_views.admin_record_detail,
        name="admin_record_detail",
    ),

    path(
        "management/records/<int:pk>/edit/",
        admin_views.admin_record_update,
        name="admin_record_update",
    ),

    path(
        "management/records/<int:pk>/delete/",
        admin_views.admin_record_delete,
        name="admin_record_delete",
    ),

    # ========================================================
    # Website Admin — Prescriptions CRUD (Phase 2)
    # ========================================================

    path(
        "management/prescriptions/",
        admin_views.admin_prescription_list,
        name="admin_prescription_list",
    ),

    path(
        "management/prescriptions/new/",
        admin_views.admin_prescription_create,
        name="admin_prescription_create",
    ),

    path(
        "management/prescriptions/<int:pk>/",
        admin_views.admin_prescription_detail,
        name="admin_prescription_detail",
    ),

    path(
        "management/prescriptions/<int:pk>/edit/",
        admin_views.admin_prescription_update,
        name="admin_prescription_update",
    ),

    path(
        "management/prescriptions/<int:pk>/delete/",
        admin_views.admin_prescription_delete,
        name="admin_prescription_delete",
    ),

    # ========================================================
    # Website Admin — Medical Examinations CRUD (Phase 3)
    # ========================================================

    path(
        "management/examinations/",
        admin_views.admin_examination_list,
        name="admin_examination_list",
    ),

    path(
        "management/examinations/new/",
        admin_views.admin_examination_create,
        name="admin_examination_create",
    ),

    path(
        "management/examinations/<int:pk>/",
        admin_views.admin_examination_detail,
        name="admin_examination_detail",
    ),

    path(
        "management/examinations/<int:pk>/edit/",
        admin_views.admin_examination_update,
        name="admin_examination_update",
    ),

    path(
        "management/examinations/<int:pk>/delete/",
        admin_views.admin_examination_delete,
        name="admin_examination_delete",
    ),

    path(
        "management/examinations/<int:pk>/download/",
        admin_views.admin_examination_download,
        name="admin_examination_download",
    ),
]
