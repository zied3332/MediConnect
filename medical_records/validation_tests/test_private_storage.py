from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.test import SimpleTestCase

from medical_records.storage import PrivateMedicalStorage


class PrivateMedicalStorageTests(SimpleTestCase):
    """Security tests for private medical file storage."""

    def setUp(self):
        self.storage = PrivateMedicalStorage()

    def test_private_files_are_outside_public_media_root(self):
        """Private files must be stored outside MEDIA_ROOT."""
        private_root = Path(self.storage.location).resolve()
        public_root = Path(settings.MEDIA_ROOT).resolve()

        self.assertNotEqual(private_root, public_root)
        self.assertNotIn(public_root, private_root.parents)

    def test_private_storage_has_no_public_url(self):
        """Private medical files must not expose public URLs."""
        with self.assertRaises(ValueError):
            self.storage.url("medical_records/example.pdf")

    def test_private_storage_uses_expected_directory(self):
        """Medical files must use the dedicated private directory."""
        expected_root = (
            Path(settings.BASE_DIR) / "private_medical_files"
        ).resolve()

        self.assertEqual(
            Path(self.storage.location).resolve(),
            expected_root,
        )

    def test_private_storage_does_not_use_media_url(self):
        """
        Django normalizes an empty base_url to "/".

        Private storage must not inherit the public MEDIA_URL,
        and public URL generation must remain disabled.
        """
        self.assertEqual(self.storage.base_url, "/")

        self.assertNotEqual(
            self.storage.base_url,
            settings.MEDIA_URL,
        )

        with self.assertRaises(ValueError):
            self.storage.url("medical_records/example.pdf")

    def test_storage_rejects_parent_directory_traversal(self):
        """Storage must reject attempts to escape its private root."""
        with self.assertRaises(
            (ValueError, SuspiciousFileOperation)
        ):
            self.storage.path("../outside.pdf")