from django.utils.translation import gettext_lazy as ui_gettext
from datetime import datetime

from django import forms
from django.utils import timezone

from accounts.models import User
from specialty.models import Specialty

from .models import Appointment


def slot_value(slot):
    """Stable string used as the radio value for a slot."""
    return timezone.localtime(slot).strftime("%Y-%m-%dT%H:%M")


class SlotChoiceMixin:
    """Adds a required `slot` radio field restricted to the given free slots."""

    def _add_slot_field(self, slots):
        self.slots = list(slots)
        self.fields["slot"] = forms.ChoiceField(
            label=ui_gettext("Time slot"),
            choices=[(slot_value(s), slot_value(s)) for s in self.slots],
            widget=forms.RadioSelect,
            error_messages={
                "required": "Please choose a time slot.",
                "invalid_choice": "This slot is no longer available. Please choose another one.",
            },
        )

    def clean_slot(self):
        naive = datetime.strptime(self.cleaned_data["slot"], "%Y-%m-%dT%H:%M")
        return timezone.make_aware(naive)


class BookingForm(SlotChoiceMixin, forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("mode", "reason")
        widgets = {
            "mode": forms.RadioSelect,
            "reason": forms.Textarea(attrs={"rows": 4, "maxlength": 1000}),
        }
        labels = {
            ui_gettext("mode"): ui_gettext("Consultation type"),
            ui_gettext("reason"): ui_gettext("Reason for the visit"),
        }
        help_texts = {
            "reason": "A few words to help the doctor prepare (symptoms, follow-up...).",
        }

    def __init__(self, *args, slots=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._add_slot_field(slots)
        self.fields["mode"].choices = Appointment.Mode.choices
        self.order_fields(("slot", "mode", "reason"))

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if len(reason) < 3:
            raise forms.ValidationError(ui_gettext("Please describe the reason in a few words."))
        return reason


class RescheduleForm(SlotChoiceMixin, forms.Form):
    def __init__(self, *args, slots=(), **kwargs):
        super().__init__(*args, **kwargs)
        self._add_slot_field(slots)


class RejectForm(forms.Form):
    reason = forms.CharField(
        label=ui_gettext("Reason (optional)"),
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2}),
    )


class SpecialtyChoiceForm(forms.Form):
    specialty = forms.ModelChoiceField(
        label=ui_gettext("Specialty"),
        queryset=Specialty.objects.all(),
        empty_label="Choose a specialty",
    )


STATUS_FILTER_CHOICES = [("", "All statuses"), *Appointment.Status.choices]


class DoctorFilterForm(forms.Form):
    WHEN_CHOICES = [("upcoming", "Upcoming"), ("past", "Past"), ("all", "All dates")]

    when = forms.ChoiceField(label=ui_gettext("Period"), choices=WHEN_CHOICES, required=False)
    status = forms.ChoiceField(label=ui_gettext("Status"), choices=STATUS_FILTER_CHOICES, required=False)
    date = forms.DateField(
        label=ui_gettext("Day"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )


class AdminFilterForm(forms.Form):
    doctor = forms.ModelChoiceField(
        label=ui_gettext("Doctor"),
        queryset=User.objects.filter(role=User.Role.DOCTOR).order_by("last_name", "first_name"),
        required=False,
        empty_label="All doctors",
    )
    patient = forms.ModelChoiceField(
        label=ui_gettext("Patient"),
        queryset=User.objects.filter(role=User.Role.PATIENT).order_by("last_name", "first_name"),
        required=False,
        empty_label="All patients",
    )
    status = forms.ChoiceField(label=ui_gettext("Status"), choices=STATUS_FILTER_CHOICES, required=False)
    date = forms.DateField(
        label=ui_gettext("Day"), required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label = lambda u: u.get_full_name() or u.email  # noqa: E731
        self.fields["doctor"].label_from_instance = label
        self.fields["patient"].label_from_instance = label
