
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from medical_records.models import DossierMedical


class AdminMedicalRecordCRUDTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = Group.objects.create(
            name="medical_crud_demo_patients"
        )

        cls.admin = User.objects.create_user(
            username="demo_admin",
            email="demo_admin@example.com",
            password="TestPassword123!",
            role="admin",
        )
        cls.patient = User.objects.create_user(
            username="demo_patient",
            email="demo_patient@example.com",
            password="TestPassword123!",
            role="patient",
        )
        cls.other_patient = User.objects.create_user(
            username="real_patient",
            email="real_patient@example.com",
            password="TestPassword123!",
            role="patient",
        )
        cls.doctor = User.objects.create_user(
            username="demo_doctor",
            email="demo_doctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        cls.patient.groups.add(cls.group)

        cls.real_record = DossierMedical.objects.create(
            patient=cls.other_patient,
            antecedents="Private medical history",
        )

    def test_admin_can_create_demo_record(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("medical_records:admin_record_create"),
            {
                "patient": self.patient.pk,
                "antecedents": "Asthma",
                "allergies": "Penicillin",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            DossierMedical.objects.filter(
                patient=self.patient,
                antecedents="Asthma",
            ).exists()
        )

    def test_admin_cannot_create_real_patient_record(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse("medical_records:admin_record_create"),
            {
                "patient": self.other_patient.pk,
                "antecedents": "Unauthorized",
                "allergies": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            DossierMedical.objects.filter(
                patient=self.other_patient
            ).count(),
            1,
        )

    def test_admin_can_read_demo_record(self):
        record = DossierMedical.objects.create(
            patient=self.patient
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "medical_records:admin_record_detail",
                args=[record.pk],
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_admin_cannot_read_real_record(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "medical_records:admin_record_detail",
                args=[self.real_record.pk],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_admin_can_update_demo_record(self):
        record = DossierMedical.objects.create(
            patient=self.patient
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_record_update",
                args=[record.pk],
            ),
            {
                "antecedents": "Updated history",
                "allergies": "Peanuts",
            },
        )

        self.assertEqual(response.status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.antecedents, "Updated history")

    def test_admin_can_delete_demo_record(self):
        record = DossierMedical.objects.create(
            patient=self.patient
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_record_delete",
                args=[record.pk],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            DossierMedical.objects.filter(pk=record.pk).exists()
        )

    def test_admin_cannot_delete_real_record(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_record_delete",
                args=[self.real_record.pk],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            DossierMedical.objects.filter(
                pk=self.real_record.pk
            ).exists()
        )

    def test_patient_cannot_access_admin_records(self):
        self.client.force_login(self.patient)

        response = self.client.get(
            reverse("medical_records:admin_record_list")
        )

        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_access_admin_records(self):
        self.client.force_login(self.doctor)

        response = self.client.get(
            reverse("medical_records:admin_record_list")
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_redirected(self):
        response = self.client.get(
            reverse("medical_records:admin_record_list")
        )

        self.assertEqual(response.status_code, 302)

    def test_get_does_not_delete_record(self):
        record = DossierMedical.objects.create(
            patient=self.patient
        )
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "medical_records:admin_record_delete",
                args=[record.pk],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DossierMedical.objects.filter(pk=record.pk).exists()
        )
