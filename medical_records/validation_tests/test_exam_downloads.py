
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from medical_records.models import DossierMedical, Examen


User = get_user_model()


class ExaminationDownloadTests(TestCase):
    """
    Verify secure medical examination downloads.

    Test authentication, patient ownership, doctor restrictions,
    missing files, and secure response headers.
    """

    @classmethod
    def setUpTestData(cls):
        # ====================================================
        # Test users
        # ====================================================

        cls.patient = User.objects.create_user(
            username="patient_download",
            email="patient.download@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.other_patient = User.objects.create_user(
            username="other_patient_download",
            email="other.download@example.com",
            password="TestPassword123!",
            role="patient",
        )

        cls.doctor = User.objects.create_user(
            username="doctor_download",
            email="doctor.download@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        cls.other_doctor = User.objects.create_user(
            username="other_doctor_download",
            email="otherdoctor.download@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        # ====================================================
        # Patient medical record
        # ====================================================

        cls.dossier = DossierMedical.objects.create(
            patient=cls.patient,
        )

        # Reference to a private file.
        # The actual file contents are mocked during download.
        cls.examen = Examen.objects.create(
            dossier=cls.dossier,
            titre="Blood Test",
            fichier="medical_records/test/exam.pdf",
        )

    def setUp(self):
        self.url = reverse(
            "medical_records:examination_download",
            kwargs={"pk": self.examen.pk},
        )

    # ========================================================
    # Authentication
    # ========================================================

    def test_anonymous_user_must_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("next=", response["Location"])

    # ========================================================
    # Patient authorization
    # ========================================================

    def test_other_patient_cannot_download(self):
        self.client.force_login(self.other_patient)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_patient_can_download_own_file(self):
        self.client.force_login(self.patient)

        file_contents = b"%PDF-1.4\nTest medical document"

        with patch.object(
            self.examen.fichier.storage,
            "open",
            return_value=ContentFile(file_contents),
        ):
            response = self.client.get(self.url)

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.streaming)

            self.assertIn(
                "attachment",
                response["Content-Disposition"],
            )

            self.assertIn(
                f"medical-examination-{self.examen.pk}.pdf",
                response["Content-Disposition"],
            )

            self.assertEqual(
                response["Cache-Control"],
                "private, no-store, max-age=0",
            )

            self.assertEqual(
                response["X-Content-Type-Options"],
                "nosniff",
            )

            self.assertEqual(
                response["Content-Type"],
                "application/octet-stream",
            )

            downloaded_content = b"".join(
                response.streaming_content
            )

            self.assertEqual(
                downloaded_content,
                file_contents,
            )

            # Do not explicitly call response.close() here.
            # Closing a FileResponse can emit request_finished,
            # which may close the test database connection.

    # ========================================================
    # Doctor authorization
    # ========================================================

    def test_unrelated_doctor_cannot_download(self):
        self.client.force_login(self.other_doctor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_without_completed_appointment_cannot_download(self):
        self.client.force_login(self.doctor)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    # ========================================================
    # Missing examinations and files
    # ========================================================

    def test_missing_examination_returns_404(self):
        self.client.force_login(self.patient)

        url = reverse(
            "medical_records:examination_download",
            kwargs={"pk": 999999},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_missing_file_returns_404(self):
        self.client.force_login(self.patient)

        with patch.object(
            self.examen.fichier.storage,
            "open",
            side_effect=FileNotFoundError,
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    # ========================================================
    # HTTP method restrictions
    # ========================================================

    def test_post_request_is_not_allowed(self):
        self.client.force_login(self.patient)

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 405)
