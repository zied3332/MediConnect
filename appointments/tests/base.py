import tempfile
from datetime import datetime, time, timedelta
from pathlib import Path

from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import DoctorProfile, User
from appointments.ml import predictor
from appointments.models import Appointment
from availability.models import Availability
from specialty.models import Specialty

PASSWORD = "StrongPassword123!"
MISSING_MODEL = Path(tempfile.gettempdir()) / "mediconnect-tests-no-model.joblib"


def make_user(email, role, **extra):
    username = email.split("@")[0]
    return User.objects.create_user(
        email=email,
        username=username,
        password=PASSWORD,
        role=role,
        first_name=extra.pop("first_name", username.capitalize()),
        last_name=extra.pop("last_name", "Test"),
        **extra,
    )


def make_doctor(email="doc@example.com", status=DoctorProfile.Status.APPROVED, specialty=None, hours=("08:00", "18:00")):
    doctor = make_user(email, User.Role.DOCTOR, main_specialty=specialty)
    DoctorProfile.objects.create(user=doctor, specialty="cardiology", status=status)
    for weekday in range(7):
        Availability.objects.create(doctor=doctor, weekday=weekday, start_time=hours[0], end_time=hours[1])
    return doctor


def at(days, hour=10, minute=0):
    """Aware datetime `days` from today at hour:minute (current timezone)."""
    day = timezone.localdate() + timedelta(days=days)
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def make_appointment(patient, doctor, start, status=Appointment.Status.PENDING, **extra):
    """Create directly in the DB (no validation), e.g. for past appointments."""
    return Appointment.objects.create(
        patient=patient, doctor=doctor, start=start, status=status, reason=extra.pop("reason", "Check-up"), **extra
    )


@override_settings(NOSHOW_MODEL_PATH=MISSING_MODEL)
class AppointmentTestCase(TestCase):
    """Approved cardiologist available every day 08:00-18:00, two patients, one admin."""

    @classmethod
    def setUpTestData(cls):
        cls.specialty = Specialty.objects.create(name="Cardiology")
        cls.doctor = make_doctor(specialty=cls.specialty)
        cls.other_doctor = make_doctor("other@example.com", specialty=cls.specialty)
        cls.patient = make_user("pat@example.com", User.Role.PATIENT)
        cls.other_patient = make_user("pat2@example.com", User.Role.PATIENT)
        cls.admin = make_user("admin@example.com", User.Role.ADMIN)

    def setUp(self):
        predictor.clear_cache()
