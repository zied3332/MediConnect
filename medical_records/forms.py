from django.utils.translation import gettext_lazy as ui_gettext

from io import BytesIO
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

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
                    "placeholder": ui_gettext("Medical history, previous conditions..."),
                }
            ),
            "allergies": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": ui_gettext("Known allergies..."),
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
                    "placeholder": ui_gettext("Medication, dosage, frequency, duration..."),
                }
            ),
            "instructions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": ui_gettext("Additional instructions..."),
                }
            ),
        }

    def clean_medicaments(self):
        medicaments = self.cleaned_data["medicaments"].strip()

        if not medicaments:
            raise ValidationError(
                ui_gettext("Please enter at least one medication.")
            )

        return medicaments


class ExamenForm(forms.ModelForm):
    """
    Form for uploading medical examination documents.

    Supported formats:
    - PDF
    - JPEG (.jpg, .jpeg)
    - PNG

    Maximum file size: 10 MB.
    """

    ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE = 10 * 1024 * 1024

    class Meta:
        model = Examen
        fields = ["titre", "fichier", "date"]

        widgets = {
            "titre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": ui_gettext("Examination title"),
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

        # 1. Validate file extension.
        if extension not in self.ALLOWED_EXTENSIONS:
            raise ValidationError(
                ui_gettext("Only PDF, JPG, JPEG and PNG files are allowed.")
            )

        # 2. Reject empty files.
        if fichier.size == 0:
            raise ValidationError(
                ui_gettext("The uploaded file cannot be empty.")
            )

        # 3. Enforce the 10 MB limit.
        if fichier.size > self.MAX_FILE_SIZE:
            raise ValidationError(
                ui_gettext("The file must not exceed 10 MB.")
            )

        # 4. Read the uploaded file.
        try:
            fichier.seek(0)
            content = fichier.read()
        except (OSError, ValueError) as exc:
            raise ValidationError(
                ui_gettext("The uploaded file could not be read.")
            ) from exc
        finally:
            try:
                fichier.seek(0)
            except (OSError, ValueError):
                pass

        # 5. Validate PDF content and structure.
        if extension == ".pdf":

            if not content.startswith(b"%PDF-"):
                raise ValidationError(
                    ui_gettext("The uploaded file is not a valid PDF.")
                )

            try:
                reader = PdfReader(
                    BytesIO(content),
                    strict=True,
                )

                if reader.is_encrypted:
                    raise ValidationError(
                        ui_gettext("Password-protected PDFs are not supported.")
                    )

                if len(reader.pages) == 0:
                    raise ValidationError(
                        ui_gettext("The PDF must contain at least one page.")
                    )

            except ValidationError:
                raise
            except Exception as exc:
                raise ValidationError(
                    ui_gettext("The PDF is damaged or has an invalid structure.")
                ) from exc

        # 6. Validate JPEG and PNG images.
        else:
            expected_format = (
                "PNG" if extension == ".png" else "JPEG"
            )

            try:
                with Image.open(BytesIO(content)) as image:

                    if image.format != expected_format:
                        raise ValidationError(
                            ui_gettext("The image content does not match "
                            "its file extension.")
                        )

                    image.verify()

            except ValidationError:
                raise
            except (
                UnidentifiedImageError,
                OSError,
                ValueError,
                SyntaxError,
            ) as exc:
                raise ValidationError(
                    ui_gettext("The uploaded image is invalid or corrupted.")
                ) from exc

        # 7. Reset the file pointer before saving.
        fichier.seek(0)

        return fichier
