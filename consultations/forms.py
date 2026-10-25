from django import forms

from .models import Consultation, Message, Avis


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ("diagnostic", "notes", "lien_visio")
        labels = {"diagnostic": "Diagnostic", "notes": "Notes du compte rendu (visibles par le patient)", "lien_visio": "Lien de visioconférence (HTTPS)"}
        widgets = {
            "diagnostic": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 5}),
            "lien_visio": forms.URLInput(attrs={"placeholder": "https://…"}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("contenu",)
        labels = {"contenu": "Votre message"}
        widgets = {"contenu": forms.Textarea(attrs={"rows": 3, "placeholder": "Écrivez au sujet de cette consultation…", "maxlength": 4000})}


class AvisForm(forms.ModelForm):
    note = forms.TypedChoiceField(label="Votre note", coerce=int, choices=[(n, f"{n} / 5 {'★' * n}") for n in range(5, 0, -1)], widget=forms.RadioSelect)

    class Meta:
        model = Avis
        fields = ("note", "commentaire")
        labels = {"commentaire": "Votre expérience"}
        widgets = {"commentaire": forms.Textarea(attrs={"rows": 4, "placeholder": "Accueil, écoute, clarté des explications… Évitez les informations médicales personnelles."})}
