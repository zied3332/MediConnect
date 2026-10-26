
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from PIL import Image
from pypdf import PdfWriter

from medical_records.forms import ExamenForm


class ExaminationFileValidationTests(SimpleTestCase):

    def make_form(self, filename, content):
        uploaded = SimpleUploadedFile(
            filename,
            content,
            content_type="application/octet-stream",
        )

        return ExamenForm(
            data={
                "titre": "Blood Test",
                "date": "2026-10-26",
            },
            files={"fichier": uploaded},
        )

    def make_image(self, image_format):
        buffer = BytesIO()

        image = Image.new("RGB", (10, 10))
        image.save(buffer, format=image_format)

        return buffer.getvalue()

    def make_pdf(self):
        buffer = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(buffer)

        return buffer.getvalue()

    def test_valid_pdf(self):
        form = self.make_form("report.pdf", self.make_pdf())
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_png(self):
        form = self.make_form(
            "scan.png",
            self.make_image("PNG"),
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_valid_jpeg(self):
        form = self.make_form(
            "scan.jpg",
            self.make_image("JPEG"),
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_invalid_extension(self):
        form = self.make_form(
            "malware.exe",
            b"not an allowed file",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_fake_pdf(self):
        form = self.make_form(
            "fake.pdf",
            b"This is not a PDF",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_corrupted_image(self):
        form = self.make_form(
            "broken.png",
            b"not a real PNG",
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_mismatched_extension(self):
        form = self.make_form(
            "scan.png",
            self.make_image("JPEG"),
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_empty_file(self):
        form = self.make_form("empty.pdf", b"")
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)

    def test_oversized_file(self):
        content = b"A" * (10 * 1024 * 1024 + 1)

        form = self.make_form(
            "large.pdf",
            content,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fichier", form.errors)
