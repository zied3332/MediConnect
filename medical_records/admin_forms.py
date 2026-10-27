
from django import forms

from appointments.models import Appointment
from consultations.models import Consultation

from .forms import ExamenForm
from .models import DossierMedical, Ordonnance


# ============================================================
# PHASE 2 — ADMIN PRESCRIPTIONS FORM
# ============================================================

class AdminOrdonnanceForm(forms.ModelForm):
    class Meta:
        model = Ordonnance

        fields = [
            "consultation",
            "date",
            "medicaments",
            "instructions",
        ]

        widgets = {
            "consultation": forms.Select(
                attrs={"class": "form-control"}
            ),
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "medicaments": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Medication, dosage, frequency...",
                }
            ),
            "instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Additional instructions...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        consultations = Consultation.objects.filter(
            appointment__status__in=[
                Appointment.Status.CONFIRMED,
                Appointment.Status.COMPLETED,
            ]
        ).select_related(
            "appointment__patient",
            "appointment__doctor",
        )

        if self.instance.pk:
            consultations = consultations.filter(
                pk=self.instance.consultation_id
            )
            self.fields["consultation"].disabled = True

        self.fields["consultation"].queryset = consultations

    def clean_medicaments(self):
        value = self.cleaned_data["medicaments"].strip()

        if not value:
            raise forms.ValidationError(
                "Please enter at least one medication."
            )

        return value


# ============================================================
# PHASE 3 — ADMIN MEDICAL EXAMINATIONS FORM
# ============================================================

class AdminExamenForm(ExamenForm):
    """
    Admin form for medical examinations.

    Reuses ExamenForm validation:
    - PDF, JPG, JPEG, PNG
    - Maximum size of 10 MB
    - PDF and image content verification
    """

    dossier = forms.ModelChoiceField(
        queryset=DossierMedical.objects.none(),
        label="Patient Medical Record",
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
    )

    class Meta(ExamenForm.Meta):
        fields = [
            "dossier",
            "titre",
            "fichier",
            "date",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        dossiers = (
            DossierMedical.objects
            .select_related("patient")
            .filter(patient__role="patient")
            .order_by(
                "patient__first_name",
                "patient__last_name",
                "patient__email",
            )
        )

        self.fields["dossier"].label_from_instance = (
            lambda dossier: (
                f"{dossier.patient.get_full_name() or dossier.patient.email}"
                f" — {dossier.patient.email}"
            )
        )

        if self.instance.pk:
            # Existing examinations cannot change patient.
            dossiers = dossiers.filter(
                pk=self.instance.dossier_id
            )
            self.fields["dossier"].disabled = True
            self.fields["dossier"].initial = self.instance.dossier

        self.fields["dossier"].queryset = dossiers
