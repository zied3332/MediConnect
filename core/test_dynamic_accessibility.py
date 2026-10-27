"""Source/render contracts complement JS tests and manual browser checks."""
from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.test import SimpleTestCase

from core.test_accessibility import Elements
from core.test_accessible_forms import render_page
from medical_records.models import DossierMedical, Examen
from consultations.forms import MessageForm


class DynamicAccessibilityTests(SimpleTestCase):
    def test_consultation_counts_are_programmatic_focus_targets(self):
        page = Paginator([], 10).get_page(1)
        for template in ("list_results.html", "inbox_results.html"):
            with self.subTest(template=template):
                tags = Elements(render_page(f"consultations/{template}", page_obj=page)).tags
                count = next(attrs for _, attrs in tags if "data-live-count" in attrs)
                self.assertEqual(count["tabindex"], "-1")
                self.assertNotIn("role", count)

    def test_brief_announcements_stay_outside_replaced_content(self):
        consultation = SimpleNamespace(pk=1, appointment_id=1)
        html = render_page("consultations/brief_review.html", consultation=consultation)
        tags = Elements(html).tags
        for attribute, role in (("data-brief-status", "status"), ("data-brief-error", "alert")):
            regions = [attrs for _, attrs in tags if attribute in attrs]
            self.assertEqual(len(regions), 1)
            self.assertEqual(regions[0]["role"], role)
            self.assertNotIn("hidden", regions[0])
            self.assertLess(html.index(attribute), html.index("data-brief-root"))
        progress = next(attrs for _, attrs in tags if attrs.get("id") == "brief-progress")
        self.assertEqual(progress["aria-hidden"], "true")
        self.assertNotIn("aria-live", progress)

    def test_risk_tooltip_retains_its_description_and_keyboard_target(self):
        appointment = SimpleNamespace(pk=1, no_show_risk=0.8, risk_level="high", risk_percent=80)
        tags = Elements(render_page("appointments/partials/risk_badge.html", appointment=appointment)).tags
        badge = next(attrs for _, attrs in tags if "data-risk-tooltip" in attrs)
        tip = next(attrs for _, attrs in tags if attrs.get("role") == "tooltip")
        self.assertEqual(badge["tabindex"], "0")
        self.assertEqual(badge["aria-describedby"], tip["id"])

    def test_conversation_log_is_named_focusable_and_has_scrolling_instructions(self):
        person = get_user_model()(pk=2, username="patient")
        consultation = SimpleNamespace(pk=1, appointment=SimpleNamespace(patient=person, doctor=person, start=None))
        tags = Elements(render_page("consultations/conversation.html", consultation=consultation,
                                    form=MessageForm(), thread=[])).tags
        log = next(attrs for _, attrs in tags if attrs.get("role") == "log")
        self.assertEqual(log["tabindex"], "0")
        self.assertEqual(log["aria-label"], "Historique des messages")
        self.assertTrue(any(attrs.get("id") == log["aria-describedby"] for _, attrs in tags))

    def test_examination_filter_has_persistent_status_and_hidden_empty_state(self):
        patient = get_user_model()(pk=2, username="patient", role="patient")
        dossier = DossierMedical(pk=1, patient=patient)
        exam = Examen(pk=1, titre="Blood test", date=date(2026, 1, 1), fichier="exam.pdf", dossier=dossier)
        html = render_page("medical_records/examination_list.html", dossier=dossier, examens=[exam])
        tags = Elements(html).tags
        status = next(attrs for _, attrs in tags if attrs.get("id") == "examFilterStatus")
        self.assertEqual(status["role"], "status")
        empty = next(attrs for _, attrs in tags if attrs.get("id") == "examNoResults")
        self.assertIn("hidden", empty)
        self.assertNotIn("aria-live", empty)
        self.assertIn(".exam-item[hidden]", html)
        self.assertIn(".exam-no-results[hidden]", html)
