
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from appointments.models import Appointment
from consultations.models import Consultation

from .forms import DossierMedicalForm, OrdonnanceForm
from .models import DossierMedical, Ordonnance


# ============================================================
# Authorization helpers
# ============================================================

def can_access_patient_record(user, patient_id):
    """Check whether a user can access a patient's medical record."""

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


def can_view_prescription(user, ordonnance):
    """Only the treating doctor or patient may view a prescription."""

    if not user.is_authenticated:
        return False

    appointment = ordonnance.consultation.appointment

    if user.role == "doctor":
        return appointment.doctor_id == user.pk

    if user.role == "patient":
        return appointment.patient_id == user.pk

    return False


def can_manage_consultation_prescriptions(user, consultation):
    """Only the consultation's doctor may manage its prescriptions."""

    if not user.is_authenticated or user.role != "doctor":
        return False

    appointment = consultation.appointment

    return (
        appointment.doctor_id == user.pk
        and appointment.status in (
            Appointment.Status.CONFIRMED,
            Appointment.Status.COMPLETED,
        )
    )


# ============================================================
# Medical records
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def my_medical_record(request):
    """Allow patients to view and update their medical records."""

    if request.user.role != "patient":
        raise PermissionDenied("Only patients can access this page.")

    dossier, _ = DossierMedical.objects.get_or_create(
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
                "Your medical record has been updated successfully.",
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
    """Allow authorized doctors to view a patient's record."""

    if request.user.role != "doctor":
        raise PermissionDenied("Only doctors can access this page.")

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
        {"dossier": dossier},
    )


# ============================================================
# Prescription list
# ============================================================

@login_required
@require_http_methods(["GET"])
def prescription_list(request):
    """List prescriptions belonging to the current patient or doctor."""

    if request.user.role == "patient":
        ordonnances = Ordonnance.objects.filter(
            consultation__appointment__patient=request.user
        )

    elif request.user.role == "doctor":
        ordonnances = Ordonnance.objects.filter(
            consultation__appointment__doctor=request.user
        )

    else:
        raise PermissionDenied(
            "Only patients and doctors can access prescriptions."
        )

    ordonnances = ordonnances.select_related(
        "consultation__appointment__patient",
        "consultation__appointment__doctor",
    )

    return render(
        request,
        "medical_records/prescription_list.html",
        {"ordonnances": ordonnances},
    )


# ============================================================
# Prescription details
# ============================================================

@login_required
@require_http_methods(["GET"])
def prescription_detail(request, pk):
    """Show one prescription to its patient or treating doctor."""

    ordonnance = get_object_or_404(
        Ordonnance.objects.select_related(
            "consultation__appointment__patient",
            "consultation__appointment__doctor",
        ),
        pk=pk,
    )

    if not can_view_prescription(request.user, ordonnance):
        raise PermissionDenied(
            "You are not authorized to view this prescription."
        )

    return render(
        request,
        "medical_records/prescription_detail.html",
        {
            "ordonnance": ordonnance,
            "can_manage": can_manage_consultation_prescriptions(
                request.user,
                ordonnance.consultation,
            ),
        },
    )


# ============================================================
# Create prescription
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def prescription_create(request, consultation_id):
    """Allow the treating doctor to create a prescription."""

    consultation = get_object_or_404(
        Consultation.objects.select_related("appointment"),
        pk=consultation_id,
    )

    if not can_manage_consultation_prescriptions(
        request.user,
        consultation,
    ):
        raise PermissionDenied(
            "You cannot create prescriptions for this consultation."
        )

    if request.method == "POST":
        form = OrdonnanceForm(request.POST)

        if form.is_valid():
            ordonnance = form.save(commit=False)
            ordonnance.consultation = consultation
            ordonnance.full_clean()
            ordonnance.save()

            messages.success(
                request,
                "Prescription created successfully.",
            )

            return redirect(
                "medical_records:prescription_detail",
                pk=ordonnance.pk,
            )
    else:
        form = OrdonnanceForm()

    return render(
        request,
        "medical_records/prescription_form.html",
        {
            "form": form,
            "consultation": consultation,
            "is_edit": False,
        },
    )


# ============================================================
# Edit prescription
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def prescription_edit(request, pk):
    """Allow the treating doctor to edit a prescription."""

    ordonnance = get_object_or_404(
        Ordonnance.objects.select_related(
            "consultation__appointment"
        ),
        pk=pk,
    )

    if not can_manage_consultation_prescriptions(
        request.user,
        ordonnance.consultation,
    ):
        raise PermissionDenied(
            "You cannot edit this prescription."
        )

    if request.method == "POST":
        form = OrdonnanceForm(
            request.POST,
            instance=ordonnance,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Prescription updated successfully.",
            )

            return redirect(
                "medical_records:prescription_detail",
                pk=ordonnance.pk,
            )
    else:
        form = OrdonnanceForm(instance=ordonnance)

    return render(
        request,
        "medical_records/prescription_form.html",
        {
            "form": form,
            "consultation": ordonnance.consultation,
            "ordonnance": ordonnance,
            "is_edit": True,
        },
    )


# ============================================================
# Delete prescription
# ============================================================

@login_required
@require_http_methods(["GET", "POST"])
def prescription_delete(request, pk):
    """Require doctor authorization and POST confirmation."""

    ordonnance = get_object_or_404(
        Ordonnance.objects.select_related(
            "consultation__appointment"
        ),
        pk=pk,
    )

    if not can_manage_consultation_prescriptions(
        request.user,
        ordonnance.consultation,
    ):
        raise PermissionDenied(
            "You cannot delete this prescription."
        )

    if request.method == "POST":
        ordonnance.delete()

        messages.success(
            request,
            "Prescription deleted successfully.",
        )

        return redirect("medical_records:prescription_list")

    return render(
        request,
        "medical_records/prescription_confirm_delete.html",
        {"ordonnance": ordonnance},
    )
