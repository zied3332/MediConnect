from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class PatientSignupTests(TestCase):
    def setUp(self):
        self.signup_url = reverse("accounts:signup")
        self.valid_data = {
            "email": "new.patient@example.com",
            "first_name": "New",
            "last_name": "Patient",
            "password": "Strong!Password_9472",
            "confirm_password": "Strong!Password_9472",
        }

    def test_successful_signup_creates_and_logs_in_patient(self):
        response = self.client.post(self.signup_url, self.valid_data, follow=True)
        user = User.objects.get(email=self.valid_data["email"])

        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertTrue(user.check_password(self.valid_data["password"]))
        self.assertEqual(response.wsgi_request.user.pk, user.pk)
        self.assertRedirects(
            response,
            reverse("dashboard:patient_overview"),
            fetch_redirect_response=False,
        )
        self.assertContains(response, f"Welcome to MediConnect, {user.first_name}!")

    def test_mismatched_passwords_are_rejected(self):
        response = self.client.post(
            self.signup_url,
            {**self.valid_data, "confirm_password": "Different!Password_9472"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Passwords do not match.")
        self.assertFalse(User.objects.filter(email=self.valid_data["email"]).exists())

    def test_password_validation_errors_are_shown(self):
        response = self.client.post(
            self.signup_url,
            {
                **self.valid_data,
                "password": "password",
                "confirm_password": "password",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["password"])
        self.assertFalse(User.objects.filter(email=self.valid_data["email"]).exists())

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            username="existing",
            email="NEW.PATIENT@example.com",
            password="Existing!Password_9472",
        )

        response = self.client.post(self.signup_url, self.valid_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email already exists.")
        self.assertEqual(User.objects.filter(email__iexact=self.valid_data["email"]).count(), 1)

    def test_missing_required_fields_are_reported(self):
        response = self.client.post(
            self.signup_url,
            {"email": self.valid_data["email"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["first_name"])
        self.assertTrue(response.context["form"].errors["last_name"])
        self.assertTrue(response.context["form"].errors["password"])
        self.assertTrue(response.context["form"].errors["confirm_password"])
        self.assertFalse(User.objects.filter(email=self.valid_data["email"]).exists())
