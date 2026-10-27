import shutil
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from PIL import Image

from accounts.models import User
from medical_records.models import DossierMedical, Examen
from medical_records.storage import private_medical_storage


def make_png(filename="examination.png"):
    buffer = BytesIO()

    image = Image.new("RGB", (12, 12), "white")
    image.save(buffer, format="PNG")

    return SimpleUploadedFile(
        filename,
        buffer.getvalue(),
        content_type="image/png",
    )


class AdminExaminationTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.temp_directory = tempfile.mkdtemp(
            prefix="mediconnect-exam-tests-"
        )

        # Isolate examination files from real private storage.
        cls.storage_patcher = patch.object(
            private_medical_storage,
            "location",
            str(Path(cls.temp_directory) / "private"),
        )
        cls.storage_patcher.start()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.storage_patcher.stop()
            shutil.rmtree(
                cls.temp_directory,
                ignore_errors=True,
            )
        finally:
            super().tearDownClass()

    # ========================================================
    # TEST SETUP
    # ========================================================

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin_exam",
            email="admin_exam@example.com",
            password="TestPassword123!",
            role="admin",
        )

        self.patient = User.objects.create_user(
            username="patient_exam",
            email="patient_exam@example.com",
            password="TestPassword123!",
            role="patient",
        )

        self.other_patient = User.objects.create_user(
            username="other_patient_exam",
            email="other_patient_exam@example.com",
            password="TestPassword123!",
            role="patient",
        )

        self.doctor = User.objects.create_user(
            username="doctor_exam",
            email="doctor_exam@example.com",
            password="TestPassword123!",
            role="doctor",
        )

        self.dossier = DossierMedical.objects.create(
            patient=self.patient,
        )

        self.other_dossier = DossierMedical.objects.create(
            patient=self.other_patient,
        )

        self.list_url = reverse(
            "medical_records:admin_examination_list"
        )

    # ========================================================
    # HELPERS
    # ========================================================

    def create_examination(self):
        return Examen.objects.create(
            dossier=self.dossier,
            titre="Blood Test",
            date="2026-10-27",
            fichier=make_png(),
        )

    def examination_url(self, name, examination):
        return reverse(
            f"medical_records:{name}",
            args=[examination.pk],
        )

    # ========================================================
    # AUTHORIZATION
    # ========================================================

    def test_anonymous_user_redirected(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 302)

    def test_patient_cannot_access_admin_list(self):
        self.client.force_login(self.patient)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_access_admin_list(self):
        self.client.force_login(self.doctor)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 403)

    def test_patient_cannot_create_examination_as_admin(self):
        self.client.force_login(self.patient)

        response = self.client.post(
            reverse(
                "medical_records:admin_examination_create"
            ),
            {
                "dossier": self.dossier.pk,
                "titre": "Unauthorized",
                "date": "2026-10-27",
                "fichier": make_png(),
            },
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            Examen.objects.filter(
                titre="Unauthorized"
            ).exists()
        )

    # ========================================================
    # LIST AND DETAILS
    # ========================================================

    def test_admin_can_view_list(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_examination_details(self):
        examination = self.create_examination()
        self.client.force_login(self.admin)

        response = self.client.get(
            self.examination_url(
                "admin_examination_detail",
                examination,
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Blood Test")

    # ========================================================
    # CREATE AND VALIDATION
    # ========================================================

    def test_admin_can_create_examination(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_examination_create"
            ),
            {
                "dossier": self.dossier.pk,
                "titre": "X-Ray",
                "date": "2026-10-27",
                "fichier": make_png(),
            },
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            Examen.objects.filter(
                titre="X-Ray",
                dossier=self.dossier,
            ).exists()
        )

    def test_invalid_extension_rejected(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_examination_create"
            ),
            {
                "dossier": self.dossier.pk,
                "titre": "Invalid",
                "date": "2026-10-27",
                "fichier": SimpleUploadedFile(
                    "invalid.txt",
                    b"Not a valid examination",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Examen.objects.count(), 0)

    def test_corrupted_image_rejected(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_examination_create"
            ),
            {
                "dossier": self.dossier.pk,
                "titre": "Corrupted",
                "date": "2026-10-27",
                "fichier": SimpleUploadedFile(
                    "corrupted.png",
                    b"This is not PNG data",
                    content_type="image/png",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Examen.objects.count(), 0)

    def test_oversized_file_rejected(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "medical_records:admin_examination_create"
            ),
            {
                "dossier": self.dossier.pk,
                "titre": "Too Large",
                "date": "2026-10-27",
                "fichier": SimpleUploadedFile(
                    "large.png",
                    b"x" * (10 * 1024 * 1024 + 1),
                    content_type="image/png",
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Examen.objects.count(), 0)

    # ========================================================
    # UPDATE
    # ========================================================

    def test_admin_can_update_title_without_replacing_file(self):
        examination = self.create_examination()
        original_file = examination.fichier.name

        self.client.force_login(self.admin)

        response = self.client.post(
            self.examination_url(
                "admin_examination_update",
                examination,
            ),
            {
                "dossier": self.dossier.pk,
                "titre": "Updated Blood Test",
                "date": "2026-10-27",
            },
        )

        self.assertEqual(response.status_code, 302)

        examination.refresh_from_db()

        self.assertEqual(
            examination.titre,
            "Updated Blood Test",
        )

        self.assertEqual(
            examination.fichier.name,
            original_file,
        )

    def test_admin_cannot_reassign_examination_to_another_patient(self):
        examination = self.create_examination()
        self.client.force_login(self.admin)

        response = self.client.post(
            self.examination_url(
                "admin_examination_update",
                examination,
            ),
            {
                "dossier": self.other_dossier.pk,
                "titre": "Updated Blood Test",
                "date": "2026-10-27",
            },
        )

        self.assertEqual(response.status_code, 302)

        examination.refresh_from_db()

        self.assertEqual(
            examination.dossier_id,
            self.dossier.pk,
        )

    # ========================================================
    # DELETE AND FILE CLEANUP
    # ========================================================

    def test_get_delete_page_does_not_delete_record(self):
        examination = self.create_examination()
        self.client.force_login(self.admin)

        response = self.client.get(
            self.examination_url(
                "admin_examination_delete",
                examination,
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            Examen.objects.filter(
                pk=examination.pk
            ).exists()
        )

    def test_delete_removes_record_and_private_file(self):
        examination = self.create_examination()
        file_name = examination.fichier.name
        storage = examination.fichier.storage

        self.assertTrue(storage.exists(file_name))

        self.client.force_login(self.admin)

        with self.captureOnCommitCallbacks(
            execute=True
        ) as callbacks:
            response = self.client.post(
                self.examination_url(
                    "admin_examination_delete",
                    examination,
                )
            )

        self.assertEqual(response.status_code, 302)
        self.assertGreaterEqual(len(callbacks), 1)

        self.assertFalse(
            Examen.objects.filter(
                pk=examination.pk
            ).exists()
        )

        self.assertFalse(storage.exists(file_name))

    def test_replacement_removes_old_file_after_commit(self):
        examination = self.create_examination()

        old_file_name = examination.fichier.name
        storage = examination.fichier.storage

        self.client.force_login(self.admin)

        with self.captureOnCommitCallbacks(
            execute=True
        ) as callbacks:
            response = self.client.post(
                self.examination_url(
                    "admin_examination_update",
                    examination,
                ),
                {
                    "dossier": self.dossier.pk,
                    "titre": "New Scan",
                    "date": "2026-10-27",
                    "fichier": make_png("replacement.png"),
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertGreaterEqual(len(callbacks), 1)

        examination.refresh_from_db()

        self.assertNotEqual(
            examination.fichier.name,
            old_file_name,
        )

        self.assertTrue(
            storage.exists(examination.fichier.name)
        )

        self.assertFalse(storage.exists(old_file_name))

    # ========================================================
    # SECURE DOWNLOAD
    # ========================================================

    def test_patient_cannot_download_from_admin_endpoint(self):
        examination = self.create_examination()
        self.client.force_login(self.patient)

        response = self.client.get(
            self.examination_url(
                "admin_examination_download",
                examination,
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_download_from_admin_endpoint(self):
        examination = self.create_examination()
        self.client.force_login(self.doctor)

        response = self.client.get(
            self.examination_url(
                "admin_examination_download",
                examination,
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_download_private_examination(self):
        examination = self.create_examination()
        self.client.force_login(self.admin)

        response = self.client.get(
            self.examination_url(
                "admin_examination_download",
                examination,
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response["Cache-Control"],
            "private, no-store, max-age=0",
        )

        self.assertEqual(
            response["X-Content-Type-Options"],
            "nosniff",
        )

        self.assertIn(
            "attachment",
            response["Content-Disposition"],
        )

        # Consume the streaming response without explicitly
        # closing it inside Django's TestCase transaction.
        content = b"".join(response.streaming_content)

        self.assertGreater(len(content), 0)