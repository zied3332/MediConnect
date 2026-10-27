"""Source/render contracts complement JS tests and manual browser checks."""
from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from core.test_accessibility import Elements
from core.test_accessible_forms import render_page
from medical_records.models import DossierMedical, Examen
from consultations.forms import MessageForm


class DynamicAccessibilityTests(SimpleTestCase):
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
