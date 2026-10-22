from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"placeholder": "you@example.com", "autocomplete": "email", "id": "login-email"}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"placeholder": "Enter your password", "autocomplete": "current-password", "id": "login-password"}
        )
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
                raise forms.ValidationError("Invalid email or password. Please try again.")
            if not user.is_active:
                raise forms.ValidationError("This account is inactive.")
            self._user = user
        return cleaned

    def get_user(self):
        return self._user


class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password", "minlength": "8", "id": "signup-password"}
        ),
        validators=[validate_password],
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"autocomplete": "new-password", "minlength": "8", "id": "signup-confirm-password"}
        ),
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "password"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "placeholder": "you@example.com", "autocomplete": "email", "id": "signup-email"
            }),
            "first_name": forms.TextInput(attrs={
                "autocomplete": "given-name", "id": "signup-first-name"
            }),
            "last_name": forms.TextInput(attrs={
                "autocomplete": "family-name", "id": "signup-last-name"
            }),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
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
        # Derive a unique username from the email local-part.
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
