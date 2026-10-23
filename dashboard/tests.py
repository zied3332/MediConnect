from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from core.models import Availability, Specialty


User = get_user_model()


class AdminUsersViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="StrongPassword123!",
            role=User.Role.ADMIN,
        )
        User.objects.create_user(
            email="doctor@example.com",
            username="doctor",
            first_name="Doctor",
            last_name="Example",
            password="StrongPassword123!",
            role=User.Role.DOCTOR,
        )
        User.objects.create_user(
            email="patient@example.com",
            username="patient",
            first_name="Patient",
            last_name="Example",
            password="StrongPassword123!",
            role=User.Role.PATIENT,
        )

    def test_admin_can_view_and_filter_users(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("dashboard:admin_users"),
            {"q": "doctor", "role": User.Role.DOCTOR},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "doctor@example.com")
        self.assertNotContains(response, "patient@example.com")

    def test_non_admin_cannot_view_user_management(self):
        patient = User.objects.get(role=User.Role.PATIENT)
        self.client.force_login(patient)

        response = self.client.get(reverse("dashboard:admin_users"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_update_user_role(self):
        self.client.force_login(self.admin)
        patient = User.objects.get(role=User.Role.PATIENT)

        response = self.client.post(
            reverse("dashboard:update_user_role", args=[patient.id]),
            {"role": User.Role.DOCTOR},
        )

        patient.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        self.assertEqual(patient.role, User.Role.DOCTOR)

    def test_invalid_role_does_not_update_user(self):
        self.client.force_login(self.admin)
        patient = User.objects.get(role=User.Role.PATIENT)

        response = self.client.post(
            reverse("dashboard:update_user_role", args=[patient.id]),
            {"role": "invalid"},
        )

        patient.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard:admin_users"))
        self.assertEqual(patient.role, User.Role.PATIENT)


class SpecialtyAvailabilityTests(TestCase):
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
        self.client.force_login(self.admin)

    def test_admin_can_create_specialty_and_assign_it_to_doctor(self):
        response = self.client.post(
            reverse("dashboard:admin_specialties"),
            {"name": "Cardiology", "description": "Heart care"},
        )
        specialty = Specialty.objects.get(name="Cardiology")
        self.assertRedirects(response, reverse("dashboard:admin_specialties"))

        response = self.client.post(
            reverse("dashboard:update_doctor_specialty", args=[self.doctor.id]),
            {"specialty": specialty.id},
        )
        self.doctor.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard:admin_specialties"))
        self.assertEqual(self.doctor.main_specialty, specialty)

    def test_overlapping_availability_is_rejected(self):
        specialty = Specialty.objects.create(name="Dermatology")
        self.doctor.main_specialty = specialty
        self.doctor.save(update_fields=["main_specialty"])
        Availability.objects.create(
            doctor=self.doctor,
            weekday=Availability.Weekday.MONDAY,
            start_time="09:00",
            end_time="12:00",
        )

        self.client.force_login(self.doctor)
        response = self.client.post(
            reverse("dashboard:doctor_availability"),
            {
                "weekday": Availability.Weekday.MONDAY,
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
        response = self.client.post(
            reverse("dashboard:doctor_availability"),
            {
                "weekday": Availability.Weekday.TUESDAY,
                "start_time": "09:00",
                "end_time": "12:00",
                "is_free": "on",
            },
        )

        slot = Availability.objects.get()
        self.assertRedirects(response, reverse("dashboard:doctor_availability"))

        response = self.client.post(
            reverse("dashboard:delete_doctor_availability", args=[slot.id])
        )
        self.assertRedirects(response, reverse("dashboard:doctor_availability"))
        self.assertFalse(Availability.objects.filter(pk=slot.id).exists())

    def test_admin_availability_page_is_read_only(self):
        response = self.client.get(reverse("dashboard:admin_availability"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Read-only view")
        self.assertNotContains(response, "Add availability")

    def test_specialty_catalogue_shows_more_only_after_four_specialties(self):
        for index in range(5):
            Specialty.objects.create(name=f"Specialty {index}")

        response = self.client.get(reverse("dashboard:admin_specialties"))

        self.assertContains(response, "More")
        self.assertEqual(response.context["catalogue_specialties"].count(), 4)

    def test_admin_can_edit_and_delete_specialty(self):
        specialty = Specialty.objects.create(
            name="Old name",
            description="Old description",
        )

        response = self.client.post(
            reverse("dashboard:edit_specialty", args=[specialty.id]),
            {
                "name": "New name",
                "description": "New description",
                "next": "dashboard:admin_specialties",
            },
        )
        specialty.refresh_from_db()
        self.assertRedirects(response, reverse("dashboard:admin_specialties"))
        self.assertEqual(specialty.name, "New name")

        response = self.client.post(
            reverse("dashboard:delete_specialty", args=[specialty.id]),
            {"next": "dashboard:admin_specialties"},
        )
        self.assertRedirects(response, reverse("dashboard:admin_specialties"))
        self.assertFalse(Specialty.objects.filter(pk=specialty.id).exists())

    def test_specialty_list_is_admin_only(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse("dashboard:specialty_list"))

        self.assertEqual(response.status_code, 403)
