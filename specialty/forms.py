from django import forms

from .models import Specialty


class SpecialtyForm(forms.ModelForm):
    class Meta:
        model = Specialty
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Cardiology"}),
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Describe this specialty"}
            ),
        }

