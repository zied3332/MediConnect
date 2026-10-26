
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from appointments.models import Appointment

from .forms import DossierMedicalForm
from .models import DossierMedical


def can_access_patient_record(user, patient_id):
    """
    Check whether a user can access a patient's medical record.

    Patients can access their own records.
    Doctors can access records of patients they have treated.
    """

    if not user.is_authenticated:
        return False

    if user.role == "patient":
        return user.pk == patient_id

    if user.role == "doctor":
        return Appointment.objects.filter(
            doctor=user,
            patient_id=patient_id,
            status=Appointment.Status.COMPLETED,
        ).exists()

    return False


@login_required
@require_http_methods(["GET", "POST"])
def my_medical_record(request):
    """
    Allow patients to view and update their own medical record.
    """

    if request.user.role != "patient":
        raise PermissionDenied(
            "Only patients can access this page."
        )

    dossier, created = DossierMedical.objects.get_or_create(
        patient=request.user
    )

    if request.method == "POST":
        form = DossierMedicalForm(
            request.POST,
            instance=dossier,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Your medical record has been updated successfully."
            )

            return redirect("medical_records:my_record")
    else:
        form = DossierMedicalForm(instance=dossier)

    return render(
        request,
        "medical_records/my_record.html",
        {
            "dossier": dossier,
            "form": form,
        },
    )


@login_required
@require_http_methods(["GET"])
def patient_medical_record(request, patient_id):
    """
    Allow authorized doctors to view a patient's medical record.
    """

    if request.user.role != "doctor":
        raise PermissionDenied(
            "Only doctors can access patient records here."
        )

    if not can_access_patient_record(request.user, patient_id):
        raise PermissionDenied(
            "You are not authorized to view this patient's record."
        )

    dossier = get_object_or_404(
        DossierMedical.objects.select_related("patient"),
        patient_id=patient_id,
    )

    return render(
        request,
        "medical_records/patient_record.html",
        {
            "dossier": dossier,
        },
    )
