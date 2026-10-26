from django.urls import reverse

from appointments.models import Appointment
from appointments.tests.base import (
    AppointmentTestCase,
    at,
    make_appointment,
)
from consultations.models import Consultation


class MedicalRecordsConsultationIntegrationTests(AppointmentTestCase):
    """Verify Module 4 actions on consultation detail pages."""

    def setUp(self):
        super().setUp()

        self.appointment = make_appointment(
            self.patient,
            self.doctor,
            at(-1),
            status=Appointment.Status.COMPLETED,
        )

        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            diagnostic="Consultation de suivi.",
            notes="Tests d'intégration du dossier médical.",
        )

        self.url = reverse(
            "consultations:detail",
            args=[self.consultation.pk],
        )

        self.record_url = reverse(
            "medical_records:patient_record",
            args=[self.patient.pk],
        )

        self.examinations_url = reverse(
            "medical_records:examination_list",
            args=[self.patient.pk],
        )

        self.prescription_url = reverse(
            "medical_records:prescription_create",
            args=[self.consultation.pk],
        )

    def test_doctor_with_completed_appointment_sees_all_actions(self):
        """The treating doctor sees all Module 4 actions after completion."""
        self.client.force_login(self.doctor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.record_url)
        self.assertContains(response, self.examinations_url)
        self.assertContains(response, self.prescription_url)

    def test_patient_cannot_see_doctor_only_actions(self):
        """
        Patients must not see doctor-only Module 4 actions.

        Patients may legitimately have medical record and examination
        links in their sidebar, so we check the doctor-only section
        and action labels instead of matching URL substrings.
        """
        self.client.force_login(self.patient)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(
            response,
            "Dossier médical du patient",
        )

        self.assertNotContains(
            response,
            "Voir le dossier médical",
        )

        self.assertNotContains(
            response,
            "Nouvelle ordonnance",
        )

        # Patients must not see the doctor-only prescription action.
        self.assertNotContains(
            response,
            self.prescription_url,
        )

    def test_confirmed_appointment_allows_prescription_only(self):
        """
        A confirmed appointment allows the treating doctor
        to create prescriptions, but does not grant access
        to the full medical record without a completed appointment.
        """
        self.appointment.status = Appointment.Status.CONFIRMED
        self.appointment.save(update_fields=["status"])

        self.client.force_login(self.doctor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.record_url)
        self.assertNotContains(response, self.examinations_url)
        self.assertContains(response, self.prescription_url)

    def test_cancelled_appointment_hides_all_medical_actions(self):
        """Cancelled appointments must not expose Module 4 actions."""
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save(update_fields=["status"])

        self.client.force_login(self.doctor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.record_url)
        self.assertNotContains(response, self.examinations_url)
        self.assertNotContains(response, self.prescription_url)

    def test_unrelated_doctor_cannot_open_consultation(self):
        """A doctor unrelated to the consultation receives HTTP 404."""
        self.client.force_login(self.other_doctor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_unrelated_patient_cannot_open_consultation(self):
        """A patient unrelated to the consultation receives HTTP 404."""
        self.client.force_login(self.other_patient)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_is_redirected_to_login(self):
        """Anonymous visitors must authenticate before accessing details."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)