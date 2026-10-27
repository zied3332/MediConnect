
from functools import wraps

from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.models import User
from .models import DossierMedical


# ============================================================
# WEBSITE ADMIN AUTHORIZATION
# ============================================================

def website_admin_required(view_func):
    """
    Restrict access to authenticated users with the admin role.
    """

    @wraps(view_func)
    @login_required(login_url="accounts:login")
    def wrapper(request, *args, **kwargs):
        if request.user.role != "admin":
            return HttpResponseForbidden("Access denied")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# QUERYSETS
# ============================================================

def eligible_patients():
    """
    Return all registered patients.

    The create form will additionally exclude patients who
    already have a medical record.
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
    Return medical records belonging to registered patients.
    """

    return DossierMedical.objects.filter(
        patient__role="patient"
    ).select_related(
        "patient"
    )


def get_medical_record(pk):
    """
    Retrieve a medical record or return 404.
    """

    return get_object_or_404(
        medical_records(),
        pk=pk,
    )


# ============================================================
# ADMIN MEDICAL RECORD FORM
# ============================================================

class AdminMedicalRecordForm(forms.ModelForm):
    """
    Form used by website administrators to create and update
    patient medical records.
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
            # A medical record cannot be reassigned to
            # another patient during an update.
            patients = patients.filter(
                pk=self.instance.patient_id
            )

            self.fields["patient"].disabled = True

        else:
            # Each patient can have only one medical record.
            # Exclude patients who already have one.
            patients = patients.filter(
                dossier_medical__isnull=True
            )

        self.fields["patient"].queryset = patients


# ============================================================
# DASHBOARD CONTEXT
# ============================================================

def admin_context(**kwargs):
    """
    Shared context for the website Admin dashboard.
    """

    return {
        "dashboard_role": "admin",
        "page_title": "Medical Records",
        "active_nav": "medical_records",
        **kwargs,
    }


# ============================================================
# READ — LIST MEDICAL RECORDS
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_record_list(request):
    """
    Display all existing patient medical records.
    """

    records = medical_records().order_by(
        "-created_at"
    )

    return render(
        request,
        "medical_records/admin/records.html",
        admin_context(
            records=records,
        ),
    )


# ============================================================
# READ — MEDICAL RECORD DETAILS
# ============================================================

@website_admin_required
@require_http_methods(["GET"])
def admin_record_detail(request, pk):
    """
    Display the details of a medical record.
    """

    record = get_medical_record(pk)

    return render(
        request,
        "medical_records/admin/detail.html",
        admin_context(
            record=record,
        ),
    )


# ============================================================
# CREATE — MEDICAL RECORD
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_record_create(request):
    """
    Create a medical record for a patient who does not
    already have one.
    """

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
# UPDATE — MEDICAL RECORD
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_record_update(request, pk):
    """
    Update medical history and allergies.

    Patient reassignment is not permitted.
    """

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
# DELETE — MEDICAL RECORD
# ============================================================

@website_admin_required
@require_http_methods(["GET", "POST"])
def admin_record_delete(request, pk):
    """
    Delete a medical record after confirmation.

    Records referenced by protected related objects,
    such as examinations, cannot be deleted.
    """

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
        admin_context(
            record=record,
        ),
    )
