
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import DossierMedical, Ordonnance, Examen


class DossierMedicalForm(forms.ModelForm):
    """Form for editing a patient's medical information."""

    class Meta:
        model = DossierMedical
        fields = ["antecedents", "allergies"]

        widgets = {
            "antecedents": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Medical history, previous conditions...",
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


class OrdonnanceForm(forms.ModelForm):
    """Form for creating and editing prescriptions."""

    class Meta:
        model = Ordonnance
        fields = ["medicaments", "instructions"]

        widgets = {
            "medicaments": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Medication, dosage, frequency, duration...",
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

    def clean_medicaments(self):
        medicaments = self.cleaned_data["medicaments"].strip()

        if not medicaments:
            raise ValidationError(
                "Please enter at least one medication."
            )

        return medicaments


class ExamenForm(forms.ModelForm):
    """Form for uploading medical examination documents."""

    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    class Meta:
        model = Examen
        fields = ["titre", "fichier", "date"]

        widgets = {
            "titre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Examination title",
                }
            ),
            "fichier": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png",
                }
            ),
            "date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
        }

    def clean_fichier(self):
        fichier = self.cleaned_data.get("fichier")

        if not fichier:
            return fichier

        extension = Path(fichier.name).suffix.lower()

        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(
                "Only PDF, JPG, JPEG and PNG files are allowed."
            )

        if fichier.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                "The file must not exceed 10 MB."
            )

        return fichier
