
from functools import wraps
from pathlib import Path

from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.http import (
    FileResponse,
    Http404,
    HttpResponseForbidden,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User

from .admin_forms import AdminOrdonnanceForm, AdminExamenForm
from .models import DossierMedical, Ordonnance, Examen


# ============================================================
# WEBSITE ADMIN AUTHORIZATION
# ============================================================

def website_admin_required(view_func):
    """Restrict access to authenticated website administrators."""

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
    """Return all registered patients."""

    return User.objects.filter(
        role="patient"
    ).order_by(
        "first_name",
        "last_name",
        "email",
    )


def medical_records():
    """Return all medical records belonging to patients."""

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
    """Admin form for creating and editing medical records."""

    class Meta:
        model = DossierMedical

        fields = [
            "patient",
            "antecedents",
            "allergies",
        ]

        widgets = {
            "patient": forms.Select(
                attrs={"class": "form-control"}
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
            patients = patients.filter(
                pk=self.instance.patient_id
            )
            self.fields["patient"].disabled = True
        else:
            patients = patients.filter(
                dossier_medical__isnull=True
            )

        self.fields["patient"].queryset = patients


# ============================================================
# DASHBOARD CONTEXT
# ============================================================

def admin_context(**kwargs):
    return {
        "dashboard_role": "admin",
        "page_title": "Medical Records",
        "active_nav": "medical_records",
        **kwargs,
    }


def admin_prescription_context(**kwargs):
    return {
        "dashboard_role": "admin",
        "page_title": "Prescriptions",
        "active_nav": "admin_prescriptions",
        **kwargs,
    }


def admin_examination_context(**kwargs):
    return {
        "dashboard_role": "admin",
        "page_title": "Medical Examinations",
        "active_nav": "admin_examinations",
        **kwargs,
    }


# ============================================================
# PHASE 1 — MEDICAL RECORDS CRUD
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


@website_admin_required
@require_http_methods(["GET"])
def admin_record_detail(request, pk):
    record = get_medical_record(pk)

    return render(
        request,
        "medical_records/admin/detail.html",
        admin_context(record=record),
    )


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
# PHASE 2 — PRESCRIPTIONS QUERYSETS
# ============================================================

def admin_prescriptions():
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
# PHASE 2 — PRESCRIPTIONS CRUD
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


# ============================================================
# PHASE 3 — MEDICAL EXAMINATIONS QUERYSETS
# ============================================================

def admin_examinations():
    return Examen.objects.select_related(
        "dossier__patient"
    )


def get_admin_examination(pk):
    return get_object_or_404(
        admin_examinations(),
        pk=pk,
    )


# ============================================================
# PHASE 3 — MEDICAL EXAMINATIONS CRUD
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_examination_list(request):
    examinations = admin_examinations().order_by(
        "-date",
        "-pk",
    )

    return render(
        request,
        "medical_records/admin/examinations.html",
        admin_examination_context(
            examinations=examinations,
        ),
    )


@website_admin_required
@require_http_methods(["GET"])
def admin_examination_detail(request, pk):
    examination = get_admin_examination(pk)

    return render(
        request,
        "medical_records/admin/examination_detail.html",
        admin_examination_context(
            examination=examination,
        ),
    )


@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_examination_create(request):
    form = AdminExamenForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == "POST" and form.is_valid():
        examination = form.save()

        return redirect(
            "medical_records:admin_examination_detail",
            pk=examination.pk,
        )

    return render(
        request,
        "medical_records/admin/examination_form.html",
        admin_examination_context(
            form=form,
            action="Create",
        ),
    )


@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_examination_update(request, pk):
    examination = get_admin_examination(pk)

    form = AdminExamenForm(
        request.POST or None,
        request.FILES or None,
        instance=examination,
    )

    if request.method == "POST" and form.is_valid():
        form.save()

        return redirect(
            "medical_records:admin_examination_detail",
            pk=examination.pk,
        )

    return render(
        request,
        "medical_records/admin/examination_form.html",
        admin_examination_context(
            form=form,
            action="Update",
            examination=examination,
        ),
    )


@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_examination_delete(request, pk):
    examination = get_admin_examination(pk)

    if request.method == "POST":
        try:
            examination.delete()
        except ProtectedError:
            return HttpResponseForbidden(
                "Cannot delete this examination because "
                "it contains protected related data."
            )

        return redirect(
            "medical_records:admin_examination_list"
        )

    return render(
        request,
        "medical_records/admin/examination_confirm_delete.html",
        admin_examination_context(
            examination=examination,
        ),
    )


# ============================================================
# PHASE 3 — SECURE ADMIN EXAMINATION DOWNLOAD
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_examination_download(request, pk):
    examination = get_admin_examination(pk)

    if not examination.fichier:
        raise Http404("Examination file not found.")

    extension = Path(
        examination.fichier.name
    ).suffix.lower()

    if extension not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise Http404("Unsupported examination file type.")

    try:
        file_handle = examination.fichier.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Examination file not found.")

    response = FileResponse(
        file_handle,
        as_attachment=True,
        filename=(
            f"medical-examination-{examination.pk}{extension}"
        ),
        content_type="application/octet-stream",
    )

    response["Cache-Control"] = "private, no-store, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-Robots-Tag"] = "noindex, nofollow"

    return response
