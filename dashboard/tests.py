from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase


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
