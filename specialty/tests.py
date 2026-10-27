from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import SpecialtyForm
from .models import Specialty


User = get_user_model()


class SpecialtyModelTests(TestCase):
    def test_string_representation_uses_name(self):
        specialty = Specialty(name="Cardiology", description="Heart care")

        self.assertEqual(str(specialty), "Cardiology")

    def test_name_is_required(self):
        form = SpecialtyForm({"name": "", "description": "Heart care"})

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_duplicate_name_is_rejected(self):
        Specialty.objects.create(name="Cardiology")

        form = SpecialtyForm({"name": "Cardiology", "description": "Updated"})

        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_description_is_optional(self):
        form = SpecialtyForm({"name": "Neurology", "description": ""})

        self.assertTrue(form.is_valid())


class SpecialtyViewTests(TestCase):
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
            reverse("specialty:admin_specialties"),
            {"name": "Cardiology", "description": "Heart care"},
        )
        specialty = Specialty.objects.get(name="Cardiology")
        self.assertRedirects(response, reverse("specialty:admin_specialties"))

        response = self.client.post(
            reverse("specialty:update_doctor_specialty", args=[self.doctor.id]),
            {"specialty": specialty.id},
        )
        self.doctor.refresh_from_db()
        self.assertRedirects(response, reverse("specialty:admin_specialties"))
        self.assertEqual(self.doctor.main_specialty, specialty)

    def test_specialty_catalogue_shows_more_only_after_four_specialties(self):
        for index in range(5):
            Specialty.objects.create(name=f"Specialty {index}")

        response = self.client.get(reverse("specialty:admin_specialties"))

        self.assertContains(response, "More")
        self.assertEqual(response.context["catalogue_specialties"].count(), 4)

    def test_admin_can_edit_and_delete_specialty(self):
        specialty = Specialty.objects.create(
            name="Old name",
            description="Old description",
        )

        response = self.client.post(
            reverse("specialty:edit_specialty", args=[specialty.id]),
            {
                "name": "New name",
                "description": "New description",
                "next": "specialty:admin_specialties",
            },
        )
        specialty.refresh_from_db()
        self.assertRedirects(response, reverse("specialty:admin_specialties"))
        self.assertEqual(specialty.name, "New name")

        response = self.client.post(
            reverse("specialty:delete_specialty", args=[specialty.id]),
            {"next": "specialty:admin_specialties"},
        )
        self.assertRedirects(response, reverse("specialty:admin_specialties"))
        self.assertFalse(Specialty.objects.filter(pk=specialty.id).exists())

    def test_specialty_list_is_admin_only(self):
        self.client.force_login(self.doctor)

        response = self.client.get(reverse("specialty:specialty_list"))

        self.assertEqual(response.status_code, 403)
