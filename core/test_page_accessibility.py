"""Page-level source/render checks; computed styles still need a browser."""
import re
from types import SimpleNamespace
from datetime import time

from django.conf import settings
from django.test import SimpleTestCase
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from appointments.models import Appointment
from consultations.models import Consultation
from medical_records.models import DossierMedical, Examen, Ordonnance
from core.test_accessible_forms import render_page
from core.test_accessibility import Elements
from core.models import Availability
from accounts.models import DoctorProfile


class PageAccessibilityTests(SimpleTestCase):
    def page_context(self):
        person = get_user_model()(pk=1, username="example", email="example@example.com", role="doctor")
        appointment = Appointment(pk=9, patient=person, doctor=person, start=timezone.now())
        consultation = Consultation(pk=7, appointment=appointment, diagnostic="PRIVATE CLINICAL TEXT")
        record = DossierMedical(pk=2, patient=person)
        prescription = Ordonnance(pk=13, consultation=consultation)
        exam = Examen(pk=11, dossier=record, titre="PRIVATE CLINICAL TEXT")
        profile = DoctorProfile(pk=1, user=person, specialty="cardiology")
        return {"consultation": consultation, "appointment": appointment, "record": record,
                "dossier": record, "prescription": prescription, "examination": exam,
                "form": forms.Form(), "action": "Create", "message": SimpleNamespace(consultation_id=7),
                "records": [record], "prescriptions": [prescription], "examinations": [exam],
                "users": [person], "doctors": [person], "profiles": [profile], "profile": profile,
                "slots": [Availability(pk=3, doctor=person, weekday=1, start_time=time(9), end_time=time(10))],
                "patients": [{"patient_id": 1, "patient__first_name": "Example", "completed_count": 1}]}

    def test_dashboard_tables_have_captions_and_explicit_header_scopes(self):
        for page in ("medical_records/admin/records", "medical_records/admin/prescriptions",
                     "medical_records/admin/examinations", "dashboard/admin/availability",
                     "dashboard/admin/doctor_list", "dashboard/admin/users", "dashboard/admin/specialties",
                     "dashboard/doctor/availability", "dashboard/doctor/patients"):
            with self.subTest(page=page):
                tags = Elements(render_page(f"{page}.html", **self.page_context())).tags
                self.assertEqual(sum(tag == "table" for tag, _ in tags), 1)
                self.assertEqual(sum(tag == "caption" for tag, _ in tags), 1)
                headers = [attrs for tag, attrs in tags if tag == "th"]
                self.assertTrue(any(attrs.get("scope") == "row" for attrs in headers))
                for attrs in headers:
                    self.assertIn(attrs.get("scope"), ("col", "row"))

    def test_detail_and_confirmation_headings_have_one_primary_heading_and_no_skips(self):
        for page in ("medical_records/admin/detail", "medical_records/admin/confirm_delete",
                     "medical_records/admin/examination_detail", "medical_records/admin/examination_confirm_delete",
                     "consultations/detail", "consultations/brief_review", "dashboard/admin/doctor_detail"):
            with self.subTest(page=page):
                tags = Elements(render_page(f"{page}.html", **self.page_context())).tags
                headings = [int(tag[1]) for tag, _ in tags if re.fullmatch(r"h[1-6]", tag)]
                self.assertEqual(headings.count(1), 1)
                previous = 0
                for level in headings:
                    self.assertLessEqual(level, previous + 1)
                    previous = level

    def test_page_titles_identify_purpose_without_clinical_details(self):
        context = self.page_context()
        groups = {
            "medical_records/admin": {
                "examinations": "Medical Examinations", "examination_detail": "Examination #11",
                "examination_form": "Create Examination", "examination_confirm_delete": "Delete Examination #11",
                "prescriptions": "Prescriptions", "prescription_detail": "Prescription #13",
                "prescription_form": "Create Prescription", "prescription_confirm_delete": "Delete Prescription #13",
            },
            "consultations": {
                "list": "My Consultations", "inbox": "Consultation Inbox", "conversation": "Messages",
                "detail": "Consultation #7", "form": "Edit Consultation", "delete": "Delete Consultation #7",
                "message_form": "Edit Consultation Message", "review_form": "Review a Consultation",
                "reviews": "Consultation Reviews", "brief_patient": "Patient Brief", "brief_review": "Prepare Patient Brief",
            },
            "dashboard/doctor": {"patients": "My Patients"},
        }
        for directory, pages in groups.items():
            for page, purpose in pages.items():
                with self.subTest(page=f"{directory}/{page}"):
                    html = render_page(f"{directory}/{page}.html", **context)
                    title = re.search(r"<title>(.*?)</title>", html, re.S)[1]
                    self.assertIn(purpose, title)
                    self.assertIn("MediConnect", title)
                    self.assertNotIn("PRIVATE CLINICAL TEXT", title)

    def source(self, path):
        return (settings.BASE_DIR / path).read_text(encoding="utf-8")

    def declaration(self, path, selector, property):
        source = re.sub(r"/\*.*?\*/", "", self.source(path), flags=re.S)
        values = []
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", source):
            if selector in [item.strip() for item in selectors.split(",")]:
                values.extend(re.findall(rf"(?<![-\w]){re.escape(property)}:\s*([^;]+)", body))
        self.assertTrue(values, (path, selector, property))
        return values[-1].strip()

    def color(self, value):
        if value.startswith("var("):
            name = value[4:].split(",")[0].rstrip(")")
            for path in ("static/css/accessibility.css", "static/css/tokens.css",
                         "static/css/dashboard/layout.css", "static/css/dashboard/medical-records-admin.css"):
                match = re.search(rf"{re.escape(name)}:\s*(#[\da-fA-F]+)", self.source(path))
                if match:
                    return self.color(match[1])
            self.fail(f"Unknown color token: {name}")
        value = value.lstrip("#")
        return "".join(char * 2 for char in value) if len(value) == 3 else value

    def contrast(self, first, second):
        def luminance(value):
            value = self.color(value)
            channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            return sum((x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4) * weight
                       for x, weight in zip(channels, (.2126, .7152, .0722)))
        low, high = sorted((luminance(first), luminance(second)))
        return (high + .05) / (low + .05)

    def test_page_text_tokens_contrast_with_the_declared_light_surfaces(self):
        for color in ("var(--mc-page-muted)", "var(--mc-page-muted-gold)"):
            for background in ("#fff", "#f8f9f6", "#f7f8f4", "#f2f0e8", "#fff0be"):
                with self.subTest(color=color, background=background):
                    self.assertGreaterEqual(self.contrast(color, background), 4.5)

    def test_examination_text_contrast_on_its_declared_parent_backgrounds(self):
        css = "static/css/dashboard/medical-examinations-admin.css"
        for selector, parent in ((".mr-page .table thead th", ".mr-page .table thead"),
                                 (".mr-page .table .text-muted", ".mr-page .mr-card"),
                                 (".mr-page .form-text", ".mr-page .mr-card"),
                                 (".mr-page dl.row dt", ".mr-page .mr-card")):
            with self.subTest(selector=selector):
                self.assertGreaterEqual(self.contrast(self.declaration(css, selector, "color"),
                    self.declaration(css, parent, "background")), 4.5)

    def test_status_and_footer_text_contrast_on_actual_declared_backgrounds(self):
        for path, selector, parent in (
            ("static/css/doctor.css", ".mc-status-badge--pending_review", ".mc-status-badge--pending_review"),
            ("templates/accounts/login.html", ".face-login-status.error", ".face-login-status.error"),
            ("static/css/footer.css", ".mc-footer-bottom p", ".mc-footer"),
        ):
            with self.subTest(path=path, selector=selector):
                self.assertGreaterEqual(self.contrast(self.declaration(path, selector, "color"),
                    self.declaration(path, parent, "background")), 4.5)

    def test_page_control_boundaries_and_focus_use_contrasting_tokens(self):
        for path, selector in (
            ("static/css/auth.css", ".mc-auth-field input"),
            ("static/css/doctor.css", ".mc-auth-field select"),
            ("static/css/dashboard/medical-examinations-admin.css", ".mr-page .form-control"),
            ("static/css/dashboard/medical-records-admin.css", ".mr-field textarea"),
            ("templates/medical_records/my_record.html", ".medical-record-form textarea"),
            ("templates/medical_records/prescription_form.html", ".rx-form-section textarea"),
        ):
            with self.subTest(path=path, selector=selector):
                border = self.declaration(path, selector, "border")
                self.assertIn("var(--mc-control-border)", border)
                self.assertGreaterEqual(self.contrast("var(--mc-control-border)", "#fff"), 3)
                outline = self.declaration(path, selector + ":focus", "outline")
                self.assertIn("var(--mc-accessible-focus)", outline)
                self.assertGreaterEqual(self.contrast("var(--mc-accessible-focus)", "#fff"), 3)
