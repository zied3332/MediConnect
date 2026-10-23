from datetime import date, timedelta

from django import forms
from django.core.exceptions import ValidationError

from accounts.models import User
from core.models import Availability, Specialty


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


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ("doctor", "weekday", "start_time", "end_time", "is_free")
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "doctor" in self.fields:
            self.fields["doctor"].queryset = User.objects.filter(
                role=User.Role.DOCTOR
            )

    def clean(self):
        cleaned = super().clean()
        doctor = cleaned.get("doctor")
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        weekday = cleaned.get("weekday")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

        if doctor and weekday is not None and start_time and end_time:
            overlapping = Availability.objects.filter(
                doctor=doctor,
                weekday=weekday,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise ValidationError(
                    "This availability overlaps another slot for the same doctor."
                )
        return cleaned


class DoctorAvailabilityForm(AvailabilityForm):
    calendar_date = forms.DateField(
        label="Day",
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta(AvailabilityForm.Meta):
        fields = ("weekday", "start_time", "end_time", "is_free")

    def __init__(self, *args, doctor=None, **kwargs):
        self.doctor = doctor
        super().__init__(*args, **kwargs)
        self.fields.pop("doctor", None)
        self.fields["weekday"].required = False
        self.fields["weekday"].widget = forms.HiddenInput()
        self.order_fields(("calendar_date", "weekday", "start_time", "end_time", "is_free"))
        self.fields["calendar_date"].widget.attrs["min"] = date.today().isoformat()
        if self.instance and self.instance.weekday is not None:
            today = date.today()
            days_until_weekday = (self.instance.weekday - today.weekday()) % 7
            self.initial["calendar_date"] = today + timedelta(days=days_until_weekday)
        elif not self.is_bound:
            self.initial["calendar_date"] = date.today()
        if self.doctor:
            self.instance.doctor = self.doctor

    def clean(self):
        cleaned = super(AvailabilityForm, self).clean()
        calendar_date = cleaned.get("calendar_date")
        if calendar_date and calendar_date < date.today():
            self.add_error("calendar_date", "Choose today or a future date.")
        if calendar_date:
            cleaned["weekday"] = calendar_date.weekday()
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        weekday = cleaned.get("weekday")

        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

        if self.doctor and weekday is not None and start_time and end_time:
            overlapping = Availability.objects.filter(
                doctor=self.doctor,
                weekday=weekday,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).exclude(pk=self.instance.pk)
            if overlapping.exists():
                raise ValidationError(
                    "This availability overlaps another slot for the same doctor."
                )
        return cleaned
