
from django.urls import path

from . import views

app_name = "medical_records"

urlpatterns = [
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
]
