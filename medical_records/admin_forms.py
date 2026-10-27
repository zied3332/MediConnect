
from django import forms
from appointments.models import Appointment
from consultations.models import Consultation

from .models import Ordonnance


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
