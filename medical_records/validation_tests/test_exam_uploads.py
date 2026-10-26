
import tempfile
from datetime import date
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from PIL import Image

from medical_records.models import DossierMedical, Examen
from medical_records.storage import private_medical_storage


User = get_user_model()


class ExaminationUploadTests(TestCase):
    """Integration tests for secure medical examination uploads."""

    @classmethod
    def setUpTestData(cls):
        cls.patient = User.objects.create_user(
            username="upload_patient",
            email="upload.patient@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.other_patient = User.objects.create_user(
            username="upload_other_patient",
            email="upload.other@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.doctor = User.objects.create_user(
            username="upload_doctor",
            email="upload.doctor@example.com",
            password="TestPassword123!",
            role="doctor",
        )

    def setUp(self):
        # Keep uploaded test files outside production storage.
        self.temp_directory = tempfile.TemporaryDirectory()

        self.original_storage_location = (
            private_medical_storage.location
        )

        private_medical_storage.location = (
            self.temp_directory.name
        )

        self.addCleanup(self.restore_storage)

        self.upload_url = reverse(
            "medical_records:examination_upload"
        )

    def restore_storage(self):
        private_medical_storage.location = (
            self.original_storage_location
        )
        self.temp_directory.cleanup()

    @staticmethod
    def make_png(filename="examination.png"):
        buffer = BytesIO()

        image = Image.new(
            "RGB",
            (10, 10),
            color="white",
        )

        image.save(buffer, format="PNG")

        return SimpleUploadedFile(
            filename,
            buffer.getvalue(),
            content_type="image/png",
        )

    def upload(self, file=None):
        return self.client.post(
            self.upload_url,
            {
                "titre": "Blood Test",
                "date": "2026-10-20",
                "fichier": file or self.make_png(),
            },
        )

    def test_anonymous_user_must_login(self):
        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response["Location"])

    def test_patient_can_open_upload_page(self):
        self.client.force_login(self.patient)

        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 200)

    def test_doctor_cannot_open_upload_page(self):
        self.client.force_login(self.doctor)

        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_upload_examination(self):
        self.client.force_login(self.doctor)

        response = self.upload()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Examen.objects.count(), 0)

    def test_patient_can_upload_valid_png(self):
        self.client.force_login(self.patient)

        response = self.upload()

        self.assertRedirects(
            response,
            reverse(
                "medical_records:examination_list",
                kwargs={"patient_id": self.patient.pk},
            ),
        )

        self.assertEqual(Examen.objects.count(), 1)

        examen = Examen.objects.get()

        self.assertEqual(examen.titre, "Blood Test")
        self.assertEqual(examen.dossier.patient, self.patient)
        self.assertEqual(examen.date, date(2026, 10, 20))

        self.assertTrue(
            examen.fichier.name.startswith(
                f"medical_records/{self.patient.pk}/exams/"
            )
        )

        self.assertTrue(
            examen.fichier.storage.exists(examen.fichier.name)
        )

    def test_patient_record_created_automatically(self):
        self.client.force_login(self.patient)

        self.assertFalse(
            DossierMedical.objects.filter(
                patient=self.patient
            ).exists()
        )

        response = self.upload()

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            DossierMedical.objects.filter(
                patient=self.patient
            ).exists()
        )

    def test_upload_is_assigned_to_authenticated_patient(self):
        self.client.force_login(self.other_patient)

        response = self.client.post(
            self.upload_url,
            {
                "titre": "Private Examination",
                "date": "2026-10-20",
                "fichier": self.make_png(),
                "patient": self.patient.pk,
                "dossier": self.patient.pk,
            },
        )

        self.assertEqual(response.status_code, 302)

        examen = Examen.objects.get()

        self.assertEqual(
            examen.dossier.patient_id,
            self.other_patient.pk,
        )

    def test_invalid_extension_is_rejected(self):
        self.client.force_login(self.patient)

        invalid_file = SimpleUploadedFile(
            "malicious.exe",
            b"invalid content",
            content_type="application/octet-stream",
        )

        response = self.upload(invalid_file)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Examen.objects.count(), 0)

    def test_corrupted_image_is_rejected(self):
        self.client.force_login(self.patient)

        corrupted_file = SimpleUploadedFile(
            "corrupted.png",
            b"this is not a real image",
            content_type="image/png",
        )

        response = self.upload(corrupted_file)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Examen.objects.count(), 0)

    def test_empty_file_is_rejected(self):
        self.client.force_login(self.patient)

        empty_file = SimpleUploadedFile(
            "empty.png",
            b"",
            content_type="image/png",
        )

        response = self.upload(empty_file)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Examen.objects.count(), 0)

    def test_upload_requires_post(self):
        self.client.force_login(self.patient)

        response = self.client.put(self.upload_url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(Examen.objects.count(), 0)
