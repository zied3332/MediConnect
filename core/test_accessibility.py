"""Rendered contracts for the shared accessibility components."""
from html.parser import HTMLParser
import re
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class SharedAccessibilityTests(SimpleTestCase):
    @staticmethod
    def contrast(first, second):
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [value / 12.92 if value <= 0.04045 else
                      ((value + 0.055) / 1.055) ** 2.4 for value in channels]
            return sum(value * weight for value, weight in
                       zip(linear, (0.2126, 0.7152, 0.0722)))
        low, high = sorted((luminance(first), luminance(second)))
        return (high + 0.05) / (low + 0.05)

    def css_token(self, file, name):
        css = (settings.BASE_DIR / file).read_text(encoding="utf-8")
        return re.search(rf"{re.escape(name)}:\s*(#[0-9a-fA-F]{{6}})", css)[1]

    def test_shared_muted_text_meets_normal_text_contrast(self):
        for file, token in (
            ("static/css/tokens.css", "--mc-text-muted"),
            ("static/css/dashboard/layout.css", "--mc-admin-muted"),
            ("static/css/dashboard/medical-records-admin.css", "--mr-muted"),
        ):
            for background in ("#ffffff", "#fbfcfa", "#f8f9f6", "#f2f0e8"):
                with self.subTest(token=token, background=background):
                    self.assertGreaterEqual(self.contrast(
                        self.css_token(file, token), background), 4.5)

    def test_shared_focus_and_control_borders_meet_nontext_contrast(self):
        for token in ("--mc-accessible-focus", "--mc-control-border"):
            for background in ("#ffffff", "#f8f9f6", "#ffeb4d"):
                with self.subTest(token=token, background=background):
                    self.assertGreaterEqual(self.contrast(self.css_token(
                        "static/css/accessibility.css", token), background), 3)

    def render_shell(self, name, **context):
        request = RequestFactory().get("/")
        request.user = get_user_model()(pk=1, username="patient", role="patient")
        return Elements(render_to_string(name, {
            "request": request, "user": request.user, **context,
        }))

    def test_dashboard_loads_dialog_controller_before_its_consumers(self):
        tags = self.render_shell("dashboard/base.html").tags
        scripts = [attrs.get("src", "").split("?")[0] for tag, attrs in tags
                   if tag == "script"]
        self.assertLess(scripts.index("/static/js/dialogs.js"),
                        scripts.index("/static/js/dashboard.js"))

    def test_face_dialogs_have_names_descriptions_and_live_feedback(self):
        for template, status_id in (("accounts/login.html", "faceLoginStatus"),
                                    ("dashboard/profile.html", "faceEnrollStatus")):
            with self.subTest(template=template):
                tags = self.render_shell(template).tags
                self.assert_dialog_contract(tags, expected_count=1)
                status = next(attrs for _, attrs in tags if attrs.get("id") == status_id)
                self.assertEqual(status["role"], "status")
                self.assertEqual(status["aria-live"], "polite")
                scripts = [attrs.get("src", "") for tag, attrs in tags if tag == "script"]
                controller = scripts.index("/static/js/dialogs.js")
                consumer = next(index for index, src in enumerate(scripts)
                                if "face-login.js" in src or "face-enroll.js" in src)
                self.assertLess(controller, consumer)

    def test_specialty_dialogs_have_resolvable_names_and_descriptions(self):
        specialty = SimpleNamespace(id=1, name="Cardiology", description="Heart care")
        for template in ("specialties.html", "specialty_list.html"):
            with self.subTest(template=template):
                tags = self.render_shell(f"dashboard/admin/{template}",
                    dashboard_role="admin", specialties=[specialty],
                    catalogue_specialties=[specialty]).tags
                self.assert_dialog_contract(tags, expected_count=2)

    def test_appointment_delete_dialog_has_name_description_and_safe_cancel(self):
        tags = Elements(render_to_string("appointments/partials/delete_modal.html")).tags
        self.assert_dialog_contract(tags, expected_count=1)
        self.assertTrue(any(tag == "button" and attrs.get("type") == "button" and
                            "data-delete-cancel" in attrs for tag, attrs in tags))

    def assert_dialog_contract(self, tags, expected_count):
        ids = [attrs["id"] for _, attrs in tags if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)))
        dialogs = [attrs for _, attrs in tags if attrs.get("role") == "dialog"]
        self.assertEqual(len(dialogs), expected_count)
        for dialog in dialogs:
            self.assertEqual(dialog["aria-modal"], "true")
            self.assertEqual(dialog["aria-hidden"], "true")
            for attribute in ("aria-labelledby", "aria-describedby"):
                self.assertIn(dialog[attribute], ids)

    def test_public_skip_link_is_first_link_and_has_focusable_target(self):
        self.assert_skip_contract("base.html")

    def test_dashboard_skip_link_is_first_link_and_has_focusable_target(self):
        self.assert_skip_contract("dashboard/base.html")

    def assert_skip_contract(self, template):
        tags = self.render_shell(template).tags
        first_link = next(attrs for tag, attrs in tags if tag == "a")
        self.assertEqual(first_link["href"], "#main-content")
        self.assertIn("mc-skip-link", first_link["class"].split())
        self.assertNotIn("mc-sr-only", first_link["class"].split())
        targets = [attrs for tag, attrs in tags if attrs.get("id") == "main-content"]
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["tabindex"], "-1")
        self.assertIn(("main", targets[0]), tags)
        self.assertTrue(any(tag == "link" and attrs.get("href", "").endswith(
            "/css/accessibility.css") for tag, attrs in tags))
