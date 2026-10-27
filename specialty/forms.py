from django.utils.translation import gettext_lazy as ui_gettext
from django import forms

from .models import Specialty


class SpecialtyForm(forms.ModelForm):
    class Meta:
        model = Specialty
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": ui_gettext("e.g. Cardiology")}),
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": ui_gettext("Describe this specialty")}
            ),
        }

