
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from consultations.models import Consultation

from .models import Ordonnance


User = get_user_model()


class PrescriptionTests(TestCase):
    """Integration tests for prescription CRUD and permissions."""

    @classmethod
    def setUpTestData(cls):
        cls.patient = User.objects.create_user(
            username="test_patient",
            email="patient@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.other_patient = User.objects.create_user(
            username="other_patient",
            email="otherpatient@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.doctor = User.objects.create_user(
            username="test_doctor",
            email="doctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        cls.other_doctor = User.objects.create_user(
            username="other_doctor",
            email="otherdoctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        cls.appointment = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            start=timezone.now() - timedelta(days=1),
            status=Appointment.Status.COMPLETED,
            reason="Routine consultation",
        )

        cls.consultation = Consultation.objects.create(
            appointment=cls.appointment,
            diagnostic="Routine checkup",
        )

        cls.prescription = Ordonnance.objects.create(
            consultation=cls.consultation,
            medicaments="Example medication",
            instructions="Example instructions",
        )

    def test_doctor_can_view_own_prescription(self):
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse(
                "medical_records:prescription_detail",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_patient_can_view_own_prescription(self):
        self.client.force_login(self.patient)

        response = self.client.get(
            reverse(
                "medical_records:prescription_detail",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_other_patient_cannot_view_prescription(self):
        self.client.force_login(self.other_patient)

        response = self.client.get(
            reverse(
                "medical_records:prescription_detail",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_other_doctor_cannot_view_prescription(self):
        self.client.force_login(self.other_doctor)

        response = self.client.get(
            reverse(
                "medical_records:prescription_detail",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.get(
            reverse(
                "medical_records:prescription_detail",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 302)

    def test_doctor_can_create_prescription(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse(
                "medical_records:prescription_create",
                args=[self.consultation.pk],
            ),
            {
                "medicaments": "Test medication 500 mg",
                "instructions": "Once daily",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Ordonnance.objects.filter(
                consultation=self.consultation,
                medicaments="Test medication 500 mg",
            ).exists()
        )

    def test_patient_cannot_create_prescription(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse(
                "medical_records:prescription_create",
                args=[self.consultation.pk],
            ),
            {
                "medicaments": "Unauthorized medication",
                "instructions": "Test",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_other_doctor_cannot_create_prescription(self):
        self.client.force_login(self.other_doctor)

        response = self.client.post(
            reverse(
                "medical_records:prescription_create",
                args=[self.consultation.pk],
            ),
            {
                "medicaments": "Unauthorized medication",
                "instructions": "Test",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_doctor_can_edit_own_prescription(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse(
                "medical_records:prescription_edit",
                args=[self.prescription.pk],
            ),
            {
                "medicaments": "Updated medication",
                "instructions": "Updated instructions",
            },
        )

        self.assertEqual(response.status_code, 302)

        self.prescription.refresh_from_db()

        self.assertEqual(
            self.prescription.medicaments,
            "Updated medication",
        )

    def test_patient_cannot_edit_prescription(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse(
                "medical_records:prescription_edit",
                args=[self.prescription.pk],
            ),
            {
                "medicaments": "Unauthorized edit",
                "instructions": "Test",
            },
        )

        self.assertEqual(response.status_code, 403)

        self.prescription.refresh_from_db()

        self.assertEqual(
            self.prescription.medicaments,
            "Example medication",
        )

    def test_other_doctor_cannot_edit_prescription(self):
        self.client.force_login(self.other_doctor)

        response = self.client.post(
            reverse(
                "medical_records:prescription_edit",
                args=[self.prescription.pk],
            ),
            {
                "medicaments": "Unauthorized edit",
                "instructions": "Test",
            },
        )

        self.assertEqual(response.status_code, 403)

    def test_doctor_can_delete_prescription(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse(
                "medical_records:prescription_delete",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Ordonnance.objects.filter(
                pk=self.prescription.pk
            ).exists()
        )

    def test_patient_cannot_delete_prescription(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse(
                "medical_records:prescription_delete",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 403)

        self.assertTrue(
            Ordonnance.objects.filter(
                pk=self.prescription.pk
            ).exists()
        )

    def test_get_request_does_not_delete_prescription(self):
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse(
                "medical_records:prescription_delete",
                args=[self.prescription.pk],
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            Ordonnance.objects.filter(
                pk=self.prescription.pk
            ).exists()
        )

    def test_empty_medication_is_rejected(self):
        self.client.force_login(self.doctor)

        response = self.client.post(
            reverse(
                "medical_records:prescription_create",
                args=[self.consultation.pk],
            ),
            {
                "medicaments": "",
                "instructions": "Test instructions",
            },
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("medicaments", form.errors)
        self.assertIn(
       "This field is required.",
       form.errors["medicaments"],
        )
        self.assertFalse(form.is_valid())
        self.assertIn("medicaments", form.errors)
        self.assertIn(
       "This field is required.",
      form.errors["medicaments"],
)


    def test_patient_only_sees_own_prescriptions(self):
        self.client.force_login(self.other_patient)

        response = self.client.get(
            reverse("medical_records:prescription_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            response.context["ordonnances"],
            [],
        )
