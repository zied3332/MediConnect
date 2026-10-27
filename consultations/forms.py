from django.utils.translation import gettext_lazy as ui_gettext
from django import forms

from .models import Consultation, Message, Avis


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ("diagnostic", "notes", "lien_visio")
        labels = {"diagnostic": ui_gettext("Diagnostic"), "notes": ui_gettext("Notes du compte rendu (visibles par le patient)"), "lien_visio": ui_gettext("Lien de visioconférence (HTTPS)")}
        widgets = {
            "diagnostic": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 5}),
            "lien_visio": forms.URLInput(attrs={"placeholder": "https://…"}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("contenu",)
        labels = {ui_gettext("contenu"): ui_gettext("Votre message")}
        widgets = {"contenu": forms.Textarea(attrs={"rows": 3, "placeholder": ui_gettext("Écrivez au sujet de cette consultation…"), "maxlength": 4000})}


class AvisForm(forms.ModelForm):
    note = forms.TypedChoiceField(label=ui_gettext("Votre note"), coerce=int, choices=[(n, f"{n} / 5 {'★' * n}") for n in range(5, 0, -1)], widget=forms.RadioSelect)

    class Meta:
        model = Avis
        fields = ("note", "commentaire")
        labels = {ui_gettext("commentaire"): ui_gettext("Votre expérience")}
        widgets = {"commentaire": forms.Textarea(attrs={"rows": 4, "placeholder": ui_gettext("Accueil, écoute, clarté des explications… Évitez les informations médicales personnelles.")})}
