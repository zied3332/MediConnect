
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from medical_records.models import DossierMedical
from medical_records.views import can_access_patient_record

from datetime import timedelta

from django.utils import timezone
from appointments.models import Appointment
User = get_user_model()


class MedicalRecordTests(TestCase):
    """
    Test patient medical record management and
    doctor authorization.
    """

    @classmethod
    def setUpTestData(cls):
        # ----------------------------------------------------
        # Users
        # ----------------------------------------------------

        cls.patient = User.objects.create_user(
            username="record_patient",
            email="record.patient@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.other_patient = User.objects.create_user(
            username="record_other_patient",
            email="record.other@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.doctor = User.objects.create_user(
            username="record_doctor",
            email="record.doctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        cls.other_doctor = User.objects.create_user(
            username="record_other_doctor",
            email="record.otherdoctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        # ----------------------------------------------------
        # Existing patient medical record
        # ----------------------------------------------------

        cls.dossier = DossierMedical.objects.create(
            patient=cls.patient,
            antecedents="Asthma",
            allergies="Penicillin",
        )

    def setUp(self):
        self.my_record_url = reverse(
            "medical_records:my_record"
        )

        self.patient_record_url = reverse(
            "medical_records:patient_record",
            kwargs={"patient_id": self.patient.pk},
        )

    # ========================================================
    # Patient medical record
    # ========================================================

    def test_anonymous_user_must_login(self):
        response = self.client.get(self.my_record_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response["Location"])

    def test_patient_can_view_own_record(self):
        self.client.force_login(self.patient)

        response = self.client.get(self.my_record_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["dossier"].patient_id,
            self.patient.pk,
        )

    def test_patient_can_update_own_record(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            self.my_record_url,
            {
                "antecedents": "Diabetes",
                "allergies": "Peanuts",
            },
        )

        self.assertRedirects(
            response,
            self.my_record_url,
        )

        self.dossier.refresh_from_db()

        self.assertEqual(
            self.dossier.antecedents,
            "Diabetes",
        )
        self.assertEqual(
            self.dossier.allergies,
            "Peanuts",
        )

    def test_patient_record_created_automatically(self):
        self.client.force_login(self.other_patient)

        self.assertFalse(
            DossierMedical.objects.filter(
                patient=self.other_patient
            ).exists()
        )

        response = self.client.get(self.my_record_url)

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            DossierMedical.objects.filter(
                patient=self.other_patient
            ).exists()
        )

    def test_patient_cannot_access_doctor_record_view(self):
        self.client.force_login(self.patient)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_edit_patient_record(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.my_record_url,
            {
                "antecedents": "Modified",
                "allergies": "Modified",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.dossier.refresh_from_db()

        self.assertEqual(
            self.dossier.antecedents,
            "Asthma",
        )

    # ========================================================
    # Doctor authorization
    # ========================================================

    def test_doctor_without_appointment_cannot_view(self):
        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_unrelated_doctor_cannot_view(self):
        self.client.force_login(self.other_doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_access_helper_rejects_unrelated_doctor(self):
        self.assertFalse(
            can_access_patient_record(
                self.other_doctor,
                self.patient.pk,
            )
        )

    def test_patient_access_helper_rejects_other_patient(self):
        self.assertFalse(
            can_access_patient_record(
                self.other_patient,
                self.patient.pk,
            )
        )

    def test_anonymous_access_helper_returns_false(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertFalse(
            can_access_patient_record(
                AnonymousUser(),
                self.patient.pk,
            )
        )

    def test_post_not_allowed_on_doctor_record_view(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.patient_record_url,
        )

        self.assertEqual(response.status_code, 405)



    # ========================================================
    # Appointment-based doctor authorization
    # ========================================================

    def create_appointment(self, status, doctor=None):
        """
        Create an appointment with the requested status.

        Historical and test appointments are created directly
        through the ORM without invoking booking workflows.
        """
        return Appointment.objects.create(
            patient=self.patient,
            doctor=doctor or self.doctor,
            start=timezone.now() - timedelta(days=2),
            duration_minutes=30,
            mode=Appointment.Mode.CABINET,
            status=status,
            reason="Medical consultation",
        )

    def test_doctor_with_completed_appointment_can_view(self):
        self.create_appointment(
            Appointment.Status.COMPLETED
        )

        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["dossier"].patient_id,
            self.patient.pk,
        )

    def test_doctor_with_pending_appointment_cannot_view(self):
        self.create_appointment(
            Appointment.Status.PENDING
        )

        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_with_confirmed_appointment_cannot_view(self):
        self.create_appointment(
            Appointment.Status.CONFIRMED
        )

        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_with_cancelled_appointment_cannot_view(self):
        self.create_appointment(
            Appointment.Status.CANCELLED
        )

        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_with_rejected_appointment_cannot_view(self):
        self.create_appointment(
            Appointment.Status.REJECTED
        )

        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_with_no_show_appointment_cannot_view(self):
        self.create_appointment(
            Appointment.Status.NO_SHOW
        )

        self.client.force_login(self.doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_unrelated_doctor_cannot_view_after_completed_appointment(self):
        self.create_appointment(
            Appointment.Status.COMPLETED,
            doctor=self.doctor,
        )

        self.client.force_login(self.other_doctor)

        response = self.client.get(self.patient_record_url)

        self.assertEqual(response.status_code, 403)

    def test_completed_appointment_grants_access_via_helper(self):
        self.create_appointment(
            Appointment.Status.COMPLETED
        )

        self.assertTrue(
            can_access_patient_record(
                self.doctor,
                self.patient.pk,
            )
        )
