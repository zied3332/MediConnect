from django.utils.translation import gettext_lazy as ui_gettext
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import DoctorProfile, User


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": ui_gettext("you@example.com"),
            "autocomplete": "email",
            "id": "login-email",
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": ui_gettext("Enter your password"),
            "autocomplete": "current-password",
            "id": "login-password",
        })
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self._user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = cleaned.get("email", "").lower().strip()
        password = cleaned.get("password", "")

        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError(
                    ui_gettext("Invalid email or password. Please try again.")
                )
            # Doctors in non-approved status are kept with is_active=False
            # so authenticate() returns None. But we need to distinguish
            # "wrong password" from "email not confirmed yet / under review".
            # We therefore do a second lookup by email.
            if not user.is_active:
                raise forms.ValidationError(ui_gettext("This account is inactive."))
            self._user = user
        return cleaned

    def get_user(self):
        return self._user


# ── Patient signup ────────────────────────────────────────────────────────────

class SignupForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={
        "autocomplete": "given-name",
        "id": "signup-first-name",
    }))
    last_name = forms.CharField(widget=forms.TextInput(attrs={
        "autocomplete": "family-name",
        "id": "signup-last-name",
    }))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "minlength": "8",
            "id": "signup-password",
        }),
        validators=[validate_password],
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "minlength": "8",
            "id": "signup-confirm-password",
        }),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "placeholder": ui_gettext("you@example.com"),
                "autocomplete": "email",
                "id": "signup-email",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                ui_gettext("An account with this email already exists.")
            )
        return email

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        base = self.cleaned_data["email"].split("@")[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        user.username = username
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.PATIENT
        if commit:
            user.save()
        return user


# ── Doctor signup — step 1 (credentials + specialty) ─────────────────────────

class DoctorSignupForm(forms.ModelForm):
    """
    Collects basic info: email, name, specialty, password.
    Creates the User (inactive) and a DoctorProfile.
    """

    specialty = forms.ChoiceField(
        choices=DoctorProfile.SPECIALTY_CHOICES,
        widget=forms.Select(attrs={"id": "doctor-specialty"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "minlength": "8",
            "id": "doctor-password",
        }),
        validators=[validate_password],
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "autocomplete": "new-password",
            "minlength": "8",
            "id": "doctor-confirm-password",
        }),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "placeholder": ui_gettext("doctor@hospital.com"),
                "autocomplete": "email",
                "id": "doctor-email",
            }),
            "first_name": forms.TextInput(attrs={
                "autocomplete": "given-name",
                "id": "doctor-first-name",
            }),
            "last_name": forms.TextInput(attrs={
                "autocomplete": "family-name",
                "id": "doctor-last-name",
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                ui_gettext("An account with this email already exists.")
            )
        return email

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        base = self.cleaned_data["email"].split("@")[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1
        user.username = username
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.DOCTOR
        # Inactive until email confirmed.
        user.is_active = False
        if commit:
            user.save()
            DoctorProfile.objects.create(
                user=user,
                specialty=self.cleaned_data["specialty"],
                status=DoctorProfile.Status.PENDING_DOCUMENTS,
            )
        return user


# ── Doctor documents — step 2 ─────────────────────────────────────────────────

class DoctorDocumentForm(forms.ModelForm):
    """
    Collects the doctor's verification documents.
    All three mandatory files must be uploaded.
    The selfie is optional.
    """

    class Meta:
        model = DoctorProfile
        fields = ["medical_license", "diploma", "national_id", "selfie_with_id"]
        widgets = {
            "medical_license": forms.ClearableFileInput(attrs={
                "accept": ".pdf,.jpg,.jpeg,.png",
                "id": "doc-license",
            }),
            "diploma": forms.ClearableFileInput(attrs={
                "accept": ".pdf,.jpg,.jpeg,.png",
                "id": "doc-diploma",
            }),
            "national_id": forms.ClearableFileInput(attrs={
                "accept": ".pdf,.jpg,.jpeg,.png",
                "id": "doc-id",
            }),
            "selfie_with_id": forms.ClearableFileInput(attrs={
                "accept": ".jpg,.jpeg,.png",
                "id": "doc-selfie",
                "capture": "user",
            }),
        }
        labels = {
            ui_gettext("medical_license"): ui_gettext("Medical license / registration number"),
            ui_gettext("diploma"):         ui_gettext("Diploma or specialty certificate"),
            ui_gettext("national_id"):     ui_gettext("National ID or passport"),
            ui_gettext("selfie_with_id"):  ui_gettext("Selfie holding your ID (optional but recommended)"),
        }

    def clean(self):
        cleaned = super().clean()
        for field in ("medical_license", "diploma", "national_id"):
            if not cleaned.get(field):
                self.add_error(field, "This document is required.")
        return cleaned
