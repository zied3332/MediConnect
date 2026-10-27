from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from consultations.models import Consultation
from medical_records.models import Ordonnance


User = get_user_model()


class PrescriptionSecurityTests(TestCase):
    """Additional authorization and integrity tests for prescriptions."""

    @classmethod
    def setUpTestData(cls):
        cls.patient = User.objects.create_user(
            username="security_patient",
            email="security.patient@example.com",
            password="TestPassword123!",
            role="patient",
        )
        cls.other_patient = User.objects.create_user(
            username="security_other_patient",
            email="security.otherpatient@example.com",
            password="TestPassword123!",
            role="patient",
        )
        cls.doctor = User.objects.create_user(
            username="security_doctor",
            email="security.doctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )
        cls.other_doctor = User.objects.create_user(
            username="security_other_doctor",
            email="security.otherdoctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        cls.appointment = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            start=timezone.now() - timedelta(days=1),
            status=Appointment.Status.COMPLETED,
            reason="Security test consultation",
        )
        cls.consultation = Consultation.objects.create(
            appointment=cls.appointment,
            diagnostic="Security test diagnosis",
        )
        cls.prescription = Ordonnance.objects.create(
            consultation=cls.consultation,
            medicaments="Original medication",
            instructions="Original instructions",
        )

    def create_url(self):
        return reverse(
            "medical_records:prescription_create",
            args=[self.consultation.pk],
        )

    def edit_url(self):
        return reverse(
            "medical_records:prescription_edit",
            args=[self.prescription.pk],
        )

    def delete_url(self):
        return reverse(
            "medical_records:prescription_delete",
            args=[self.prescription.pk],
        )

    def test_unrelated_doctor_cannot_delete_prescription(self):
        self.client.force_login(self.other_doctor)

        response = self.client.post(self.delete_url())

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Ordonnance.objects.filter(pk=self.prescription.pk).exists()
        )

    def test_anonymous_user_cannot_create_prescription(self):
        response = self.client.post(
            self.create_url(),
            {"medicaments": "Unauthorized", "instructions": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ordonnance.objects.count(), 1)

    def test_confirmed_appointment_allows_prescription_creation(self):
        self.appointment.status = Appointment.Status.CONFIRMED
        self.appointment.save(update_fields=["status"])
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.create_url(),
            {"medicaments": "Confirmed medication", "instructions": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Ordonnance.objects.count(), 2)

    def test_pending_appointment_blocks_prescription_creation(self):
        self.appointment.status = Appointment.Status.PENDING
        self.appointment.save(update_fields=["status"])
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.create_url(),
            {"medicaments": "Unauthorized", "instructions": ""},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Ordonnance.objects.count(), 1)

    def test_cancelled_appointment_blocks_prescription_creation(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save(update_fields=["status"])
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.create_url(),
            {"medicaments": "Unauthorized", "instructions": ""},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Ordonnance.objects.count(), 1)

    def test_cancelled_appointment_blocks_prescription_edit(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save(update_fields=["status"])
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.edit_url(),
            {"medicaments": "Unauthorized edit", "instructions": ""},
        )

        self.assertEqual(response.status_code, 403)
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.medicaments, "Original medication")

    def test_cancelled_appointment_blocks_prescription_delete(self):
        self.appointment.status = Appointment.Status.CANCELLED
        self.appointment.save(update_fields=["status"])
        self.client.force_login(self.doctor)

        response = self.client.post(self.delete_url())

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Ordonnance.objects.filter(pk=self.prescription.pk).exists()
        )

    def test_spoofed_consultation_field_cannot_reassign_prescription(self):
        self.client.force_login(self.doctor)

        other_appointment = Appointment.objects.create(
            patient=self.other_patient,
            doctor=self.other_doctor,
            start=timezone.now() - timedelta(days=2),
            status=Appointment.Status.COMPLETED,
            reason="Other consultation",
        )
        other_consultation = Consultation.objects.create(
            appointment=other_appointment,
            diagnostic="Other diagnosis",
        )

        response = self.client.post(
            self.edit_url(),
            {
                "medicaments": "Updated medication",
                "instructions": "Updated instructions",
                "consultation": other_consultation.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.prescription.refresh_from_db()
        self.assertEqual(
            self.prescription.consultation_id,
            self.consultation.pk,
        )

    def test_spoofed_consultation_field_cannot_redirect_creation(self):
        self.client.force_login(self.doctor)

        other_appointment = Appointment.objects.create(
            patient=self.other_patient,
            doctor=self.other_doctor,
            start=timezone.now() - timedelta(days=2),
            status=Appointment.Status.COMPLETED,
            reason="Other consultation",
        )
        other_consultation = Consultation.objects.create(
            appointment=other_appointment,
            diagnostic="Other diagnosis",
        )

        response = self.client.post(
            self.create_url(),
            {
                "medicaments": "New medication",
                "instructions": "",
                "consultation": other_consultation.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        created = Ordonnance.objects.get(medicaments="New medication")
        self.assertEqual(created.consultation_id, self.consultation.pk)

    def test_invalid_medication_does_not_modify_existing_prescription(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            self.edit_url(),
            {"medicaments": "   ", "instructions": "Changed instructions"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("medicaments", response.context["form"].errors)

        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.medicaments, "Original medication")
        self.assertEqual(self.prescription.instructions, "Original instructions")

    def test_patient_cannot_view_another_patients_prescription_list(self):
        self.client.force_login(self.other_patient)

        response = self.client.get(
            reverse("medical_records:prescription_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            self.prescription,
            list(response.context["ordonnances"]),
        )

    def test_doctor_cannot_view_unrelated_prescriptions_in_list(self):
        self.client.force_login(self.other_doctor)

        response = self.client.get(
            reverse("medical_records:prescription_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(
            self.prescription,
            list(response.context["ordonnances"]),
        )