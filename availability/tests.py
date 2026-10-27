from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .forms import AvailabilityForm, DoctorAvailabilityForm
from .models import Availability


class AvailabilityModelTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email="model-doctor@example.com",
            username="model-doctor",
            password="test-password",
            role=User.Role.DOCTOR,
        )

    def test_end_time_must_be_after_start_time(self):
        slot = Availability(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time=time(12, 0),
            end_time=time(9, 0),
        )

        with self.assertRaises(ValidationError):
            slot.full_clean()

    def test_overlapping_slots_are_rejected(self):
        Availability.objects.create(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        overlapping = Availability(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time=time(11, 0),
            end_time=time(13, 0),
        )

        with self.assertRaisesMessage(
            ValidationError,
            "This availability overlaps another slot for the same doctor.",
        ):
            overlapping.full_clean()

    def test_non_overlapping_slots_are_valid(self):
        Availability.objects.create(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        slot = Availability(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time=time(12, 0),
            end_time=time(13, 0),
        )

        slot.full_clean()

    def test_string_representation_contains_doctor_day_and_time(self):
        slot = Availability(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )

        self.assertIn("Monday", str(slot))
        self.assertIn("09:00-12:00", str(slot))


class AvailabilityFormTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            email="form-doctor@example.com",
            username="form-doctor",
            password="test-password",
            role=User.Role.DOCTOR,
        )

    def test_doctor_form_places_calendar_date_before_times(self):
        form = DoctorAvailabilityForm(doctor=self.doctor)

        self.assertEqual(
            list(form.fields),
            ["calendar_date", "weekday", "start_time", "end_time", "is_free"],
        )
        self.assertEqual(form.fields["calendar_date"].widget.input_type, "date")

    def test_doctor_form_rejects_past_dates(self):
        yesterday = date.today() - timedelta(days=1)
        form = DoctorAvailabilityForm(
            {
                "calendar_date": yesterday.isoformat(),
                "start_time": "09:00",
                "end_time": "12:00",
                "is_free": "on",
            },
            doctor=self.doctor,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("calendar_date", form.errors)

    def test_calendar_date_is_converted_to_weekday(self):
        next_day = date.today() + timedelta(days=1)
        form = DoctorAvailabilityForm(
            {
                "calendar_date": next_day.isoformat(),
                "start_time": "09:00",
                "end_time": "12:00",
                "is_free": "on",
            },
            doctor=self.doctor,
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["weekday"], next_day.weekday())

    def test_form_rejects_invalid_time_order(self):
        form = AvailabilityForm(
            {
                "doctor": self.doctor.pk,
                "weekday": Availability.Weekday.MONDAY,
                "start_time": "13:00",
                "end_time": "09:00",
                "is_free": "on",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)


class AvailabilityViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin2@example.com",
            username="admin2",
            password="StrongPassword123!",
            role=User.Role.ADMIN,
        )
        self.doctor = User.objects.create_user(
            email="doctor2@example.com",
            username="doctor2",
            first_name="Doctor",
            last_name="Two",
            password="StrongPassword123!",
            role=User.Role.DOCTOR,
        )

    def test_overlapping_availability_is_rejected(self):
        Availability.objects.create(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time="09:00",
            end_time="12:00",
        )
        today = date.today()
        next_monday = today + timedelta(
            days=(Availability.Weekday.MONDAY - today.weekday()) % 7
        )

        self.client.force_login(self.doctor)
        response = self.client.post(
            reverse("availability:doctor_availability"),
            {
                "calendar_date": next_monday.isoformat(),
                "start_time": "11:00",
                "end_time": "13:00",
                "is_free": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "overlaps another slot")
        self.assertEqual(Availability.objects.count(), 1)

    def test_doctor_can_create_and_delete_only_own_slot(self):
        self.client.force_login(self.doctor)
        today = date.today()
        next_tuesday = today + timedelta(
            days=(Availability.Weekday.TUESDAY - today.weekday()) % 7
        )
        response = self.client.post(
            reverse("availability:doctor_availability"),
            {
                "calendar_date": next_tuesday.isoformat(),
                "start_time": "09:00",
                "end_time": "12:00",
                "is_free": "on",
            },
        )

        slot = Availability.objects.get()
        self.assertRedirects(response, reverse("availability:doctor_availability"))

        response = self.client.post(
            reverse("availability:delete_doctor_availability", args=[slot.id])
        )
        self.assertRedirects(response, reverse("availability:doctor_availability"))
        self.assertFalse(Availability.objects.filter(pk=slot.id).exists())

    def test_admin_availability_page_is_read_only(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("availability:admin_availability"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Read-only view")
        self.assertNotContains(response, "Add availability")
