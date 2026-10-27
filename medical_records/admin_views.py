
from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User

from .admin_forms import AdminOrdonnanceForm
from .models import DossierMedical, Ordonnance


# ============================================================
# WEBSITE ADMIN AUTHORIZATION
# ============================================================

def website_admin_required(view_func):
    """
    Restrict access to authenticated website administrators.
    """

    @wraps(view_func)
    @login_required(login_url="accounts:login")
    def wrapper(request, *args, **kwargs):
        if request.user.role != "admin":
            return HttpResponseForbidden("Access denied")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# MEDICAL RECORDS — QUERYSETS
# ============================================================

def eligible_patients():
    """
    Return all registered patients.
    """

    return User.objects.filter(
        role="patient"
    ).order_by(
        "first_name",
        "last_name",
        "email",
    )


def medical_records():
    """
    Return all medical records belonging to patients.
    """

    return DossierMedical.objects.filter(
        patient__role="patient"
    ).select_related(
        "patient"
    )


def get_medical_record(pk):
    return get_object_or_404(
        medical_records(),
        pk=pk,
    )


# ============================================================
# MEDICAL RECORDS — FORM
# ============================================================

class AdminMedicalRecordForm(forms.ModelForm):
    """
    Website Admin form for creating and editing medical records.
    """

    class Meta:
        model = DossierMedical

        fields = [
            "patient",
            "antecedents",
            "allergies",
        ]

        widgets = {
            "patient": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "antecedents": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Medical history, previous conditions..."
                    ),
                }
            ),

            "allergies": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Known allergies...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        patients = eligible_patients()

        if self.instance.pk:
            # Prevent reassignment of an existing medical record.
            patients = patients.filter(
                pk=self.instance.patient_id
            )
            self.fields["patient"].disabled = True

        else:
            # One medical record per patient.
            patients = patients.filter(
                dossier_medical__isnull=True
            )

        self.fields["patient"].queryset = patients


# ============================================================
# DASHBOARD CONTEXT
# ============================================================

def admin_context(**kwargs):
    """
    Shared dashboard context for medical record pages.
    """

    return {
        "dashboard_role": "admin",
        "page_title": "Medical Records",
        "active_nav": "medical_records",
        **kwargs,
    }


def admin_prescription_context(**kwargs):
    """
    Shared dashboard context for prescription pages.
    """

    return {
        "dashboard_role": "admin",
        "page_title": "Prescriptions",
        "active_nav": "admin_prescriptions",
        **kwargs,
    }


# ============================================================
# MEDICAL RECORDS — LIST
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_record_list(request):
    records = medical_records().order_by("-created_at")

    return render(
        request,
        "medical_records/admin/records.html",
        admin_context(records=records),
    )


# ============================================================
# MEDICAL RECORDS — DETAIL
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_record_detail(request, pk):
    record = get_medical_record(pk)

    return render(
        request,
        "medical_records/admin/detail.html",
        admin_context(record=record),
    )


# ============================================================
# MEDICAL RECORDS — CREATE
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_record_create(request):
    form = AdminMedicalRecordForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        record = form.save()

        return redirect(
            "medical_records:admin_record_detail",
            pk=record.pk,
        )

    return render(
        request,
        "medical_records/admin/form.html",
        admin_context(
            form=form,
            action="Create",
        ),
    )


# ============================================================
# MEDICAL RECORDS — UPDATE
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_record_update(request, pk):
    record = get_medical_record(pk)

    form = AdminMedicalRecordForm(
        request.POST or None,
        instance=record,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        return redirect(
            "medical_records:admin_record_detail",
            pk=record.pk,
        )

    return render(
        request,
        "medical_records/admin/form.html",
        admin_context(
            form=form,
            action="Update",
        ),
    )


# ============================================================
# MEDICAL RECORDS — DELETE
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_record_delete(request, pk):
    record = get_medical_record(pk)

    if request.method == "POST":
        try:
            record.delete()

        except ProtectedError:
            return HttpResponseForbidden(
                "Cannot delete this medical record because "
                "it contains protected related data."
            )

        return redirect(
            "medical_records:admin_record_list"
        )

    return render(
        request,
        "medical_records/admin/confirm_delete.html",
        admin_context(record=record),
    )


# ============================================================
# PRESCRIPTIONS — QUERYSETS
# ============================================================

def admin_prescriptions():
    """
    Return prescriptions with consultation and appointment data.
    """

    return Ordonnance.objects.select_related(
        "consultation__appointment__patient",
        "consultation__appointment__doctor",
    )


def get_admin_prescription(pk):
    return get_object_or_404(
        admin_prescriptions(),
        pk=pk,
    )


# ============================================================
# PRESCRIPTIONS — LIST
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_prescription_list(request):
    prescriptions = admin_prescriptions().order_by(
        "-date",
        "-pk",
    )

    return render(
        request,
        "medical_records/admin/prescriptions.html",
        admin_prescription_context(
            prescriptions=prescriptions,
        ),
    )


# ============================================================
# PRESCRIPTIONS — DETAIL
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_prescription_detail(request, pk):
    prescription = get_admin_prescription(pk)

    return render(
        request,
        "medical_records/admin/prescription_detail.html",
        admin_prescription_context(
            prescription=prescription,
        ),
    )


# ============================================================
# PRESCRIPTIONS — CREATE
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_prescription_create(request):
    form = AdminOrdonnanceForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():
        prescription = form.save()

        return redirect(
            "medical_records:admin_prescription_detail",
            pk=prescription.pk,
        )

    return render(
        request,
        "medical_records/admin/prescription_form.html",
        admin_prescription_context(
            form=form,
            action="Create",
        ),
    )


# ============================================================
# PRESCRIPTIONS — UPDATE
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_prescription_update(request, pk):
    prescription = get_admin_prescription(pk)

    form = AdminOrdonnanceForm(
        request.POST or None,
        instance=prescription,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        return redirect(
            "medical_records:admin_prescription_detail",
            pk=prescription.pk,
        )

    return render(
        request,
        "medical_records/admin/prescription_form.html",
        admin_prescription_context(
            form=form,
            action="Update",
            prescription=prescription,
        ),
    )


# ============================================================
# PRESCRIPTIONS — DELETE
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_prescription_delete(request, pk):
    prescription = get_admin_prescription(pk)

    if request.method == "POST":
        try:
            prescription.delete()

        except ProtectedError:
            return HttpResponseForbidden(
                "Cannot delete this prescription because "
                "it contains protected related data."
            )

        return redirect(
            "medical_records:admin_prescription_list"
        )

    return render(
        request,
        "medical_records/admin/prescription_confirm_delete.html",
        admin_prescription_context(
            prescription=prescription,
        ),
    )
