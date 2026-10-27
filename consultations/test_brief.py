from django.utils.translation import gettext
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import override_settings, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from appointments.tests.base import AppointmentTestCase, at, make_appointment
from .ai import BriefError, SECTIONS, generate_cards, source_data, source_hash, validate_cards, find_source_excerpt
from .models import PatientBrief
from .tasks import generate_patient_brief


class CitationTypographyTests(SimpleTestCase):
    def test_apostrophes_match_but_return_original_typography(self):
        source = "Préambule. Aucun traitement n’est prescrit. Fin."
        self.assertEqual(find_source_excerpt(source, "Aucun traitement n'est prescrit."), "Aucun traitement n’est prescrit.")
        self.assertEqual(find_source_excerpt("Il n'est pas prévu de suivi.", "Il n’est pas prévu de suivi."), "Il n'est pas prévu de suivi.")

    def test_spaces_and_line_breaks_match_without_rewriting_source(self):
        source = "Début. Noter\u00a0ses\n  questions pour\tla suite. Fin."
        self.assertEqual(find_source_excerpt(source, "Noter ses questions pour la suite."), "Noter\u00a0ses\n  questions pour\tla suite.")

    def test_changed_negation_numbers_words_and_accents_do_not_match(self):
        source = "Aucun traitement n’est prescrit. Suivi dans 10 jours. État stable."
        for quote in ("Un traitement est prescrit.", "Suivi dans 1 jours.", "Suivi dans 20 jours.", "État instable.", "Etat stable."):
            with self.subTest(quote=quote):
                self.assertIsNone(find_source_excerpt(source, quote))

    def test_validated_cards_keep_real_source_and_reject_wrong_citation(self):
        source = {"diagnostic": "Aucun nouveau diagnostic n’est établi.", "notes": ""}
        cards = [{"key": key, "text": "Non précisé dans le compte rendu.", "sources": []} for key, title in SECTIONS]
        cards[0] = {"key": "constat", "text": "Aucun nouveau diagnostic.", "sources": [{"field": "diagnostic", "quote": "Aucun nouveau diagnostic n'est établi."}]}
        self.assertEqual(validate_cards(cards, source)[0]["sources"][0]["quote"], source["diagnostic"])
        cards[0]["sources"][0]["quote"] = "Un nouveau diagnostic est établi."
        with self.assertRaises(BriefError):
            validate_cards(cards, source)


@override_settings(ANTHROPIC_API_KEY="synthetic-test-key", ANTHROPIC_MODEL="test-model")
class PatientBriefTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        from .models import Consultation
        appointment = make_appointment(self.patient, self.doctor, at(-1), status=Appointment.Status.COMPLETED)
        self.consultation = Consultation.objects.create(appointment=appointment, diagnostic="Compte rendu fictif de suivi.", notes="Noter les questions pour le prochain échange.")
        self.cards = [
            {"key": "constat", "text": "Un suivi a été réalisé.", "sources": [{"field": "diagnostic", "quote": self.consultation.diagnostic}]},
            {"key": "consignes", "text": "Notez vos questions pour le prochain échange.", "sources": [{"field": "notes", "quote": self.consultation.notes}]},
            {"key": "suivi", "text": "Non précisé dans le compte rendu.", "sources": []},
        ]

    def brief(self, **changes):
        values = {"consultation": self.consultation, "status": "ready", "source_hash": source_hash(self.consultation), "cards": validate_cards(self.cards, source_data(self.consultation))}
        values.update(changes)
        return PatientBrief.objects.create(**values)

    def url(self, name):
        return reverse(f"consultations:{name}", args=[self.consultation.pk])

    def approval(self, brief):
        return {"generation_id": str(brief.generation_id), "constat": "Texte vérifié par le médecin.", "consignes": "Notez vos questions.", "suivi": "Non précisé dans le compte rendu.", "confirm": "on"}

    def test_doctor_can_review_draft_but_patient_and_strangers_cannot(self):
        self.brief()
        self.client.force_login(self.doctor)
        self.assertRedirects(self.client.get(self.url("brief")), reverse("consultations:edit", args=[self.consultation.appointment_id]))
        for user, status in ((self.patient, 302), (self.other_patient, 404), (self.other_doctor, 404), (self.admin, 404)):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url("brief")).status_code, status)

    def test_publication_requires_confirmation_then_patient_can_read(self):
        brief = self.brief()
        self.client.force_login(self.doctor)
        data = self.approval(brief)
        del data["confirm"]
        self.client.post(self.url("brief_publish"), data)
        brief.refresh_from_db()
        self.assertEqual(brief.status, "ready")
        self.client.post(self.url("brief_publish"), self.approval(brief))
        brief.refresh_from_db()
        self.assertEqual(brief.status, "published")
        self.assertEqual(brief.published_by, self.doctor)
        self.client.force_login(self.patient)
        self.assertRedirects(self.client.get(self.url("brief")), reverse("consultations:detail", args=[self.consultation.pk]))
        self.assertEqual(self.client.post(self.url("brief_publish"), self.approval(brief)).status_code, 403)

    def test_fragment_contains_workspace_without_duplicate_dashboard(self):
        self.brief()
        self.client.force_login(self.doctor)
        response = self.client.get(self.url("brief"), {"fragment": "1"})
        self.assertRedirects(response, reverse("consultations:edit", args=[self.consultation.appointment_id]))

    def test_consultation_links_to_replacement_copilot(self):
        self.client.force_login(self.doctor)
        response = self.client.get(reverse("consultations:detail", args=[self.consultation.pk]))
        self.assertContains(response, reverse("consultations:edit", args=[self.consultation.appointment_id])+"#copilot")
        self.assertNotContains(response, "data-brief-open")

    def test_json_publication_returns_result_without_redirect(self):
        brief = self.brief()
        self.client.force_login(self.doctor)
        data = self.approval(brief)
        del data["confirm"]
        response = self.client.post(self.url("brief_publish"), data, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
        response = self.client.post(self.url("brief_publish"), self.approval(brief), HTTP_ACCEPT="application/json")
        self.assertEqual(response.json(), {"published": True})
        self.assertNotIn("Location", response)

    def test_stale_json_publication_is_rejected_without_redirect(self):
        brief = self.brief()
        self.consultation.notes = "Texte modifié."
        self.consultation.save()
        self.client.force_login(self.doctor)
        response = self.client.post(self.url("brief_publish"), self.approval(brief), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 409)
        brief.refresh_from_db()
        self.assertEqual(brief.status, "ready")

    def test_patient_cannot_fetch_unpublished_fragment(self):
        self.brief()
        self.client.force_login(self.patient)
        response = self.client.get(self.url("brief"), {"fragment": "1"})
        self.assertRedirects(response, reverse("consultations:detail", args=[self.consultation.pk]))

    def test_source_change_hides_published_brief_and_blocks_old_approval(self):
        brief = self.brief(status="published", approved_cards=[{"key": "constat", "title": "Constat", "text": "Ancienne version"}])
        self.consultation.notes = "Compte rendu modifié."
        self.consultation.save()
        self.client.force_login(self.patient)
        self.assertRedirects(self.client.get(self.url("brief")), reverse("consultations:detail", args=[self.consultation.pk]))
        self.assertNotContains(self.client.get(reverse("consultations:detail", args=[self.consultation.pk])), "Lire ma fiche patient")
        self.client.force_login(self.doctor)
        self.client.post(self.url("brief_publish"), self.approval(brief))
        brief.refresh_from_db()
        self.assertEqual(brief.approved_cards[0]["text"], "Ancienne version")

    def test_generation_requires_explicit_transfer_confirmation_and_owner(self):
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.post(self.url("brief_generate")).status_code, 400)
        self.assertEqual(self.client.get(self.url("brief_generate")).status_code, 405)
        self.client.force_login(self.other_doctor)
        self.assertEqual(self.client.post(self.url("brief_generate"), {"consent": "yes"}).status_code, 404)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.post(self.url("brief_generate"), {"consent": "yes"}).status_code, 403)
        self.assertEqual(self.client.get(self.url("brief_status")).status_code, 403)

    @patch("consultations.brief_views.generate_patient_brief.apply_async")
    def test_generation_queues_after_commit_and_blocks_duplicate(self, queue):
        self.client.force_login(self.doctor)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url("brief_generate"), {"consent": "yes"})
        self.assertEqual(response.status_code, 202)
        queue.assert_called_once()
        self.assertEqual(self.client.post(self.url("brief_generate"), {"consent": "yes"}).status_code, 409)

    @patch("consultations.brief_views.generate_patient_brief.apply_async", side_effect=RuntimeError("secret-provider-message"))
    def test_queue_failure_is_safe_and_reported(self, queue):
        self.client.force_login(self.doctor)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.url("brief_generate"), {"consent": "yes"})
        response = self.client.get(self.url("brief_status"))
        self.assertEqual(response.json()["status"], "failed")
        self.assertNotContains(response, "secret-provider-message")

    @override_settings(ANTHROPIC_API_KEY="")
    def test_missing_key_is_explicit(self):
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.post(self.url("brief_generate"), {"consent": "yes"}).status_code, 503)

    def test_status_expires_stuck_job_without_exposing_content(self):
        brief = self.brief(status="pending")
        PatientBrief.objects.filter(pk=brief.pk).update(updated_at=timezone.now() - timedelta(minutes=4))
        self.client.force_login(self.doctor)
        response = self.client.get(self.url("brief_status"))
        self.assertEqual(response.json()["status"], "failed")
        self.assertNotContains(response, self.consultation.diagnostic)

    @patch("consultations.tasks.generate_cards")
    def test_worker_persists_ready_draft_and_ignores_obsolete_job(self, generate):
        brief = self.brief(status="pending")
        generate.return_value = (self.cards, 123, "test-model")
        generate_patient_brief(brief.pk, str(brief.generation_id))
        brief.refresh_from_db()
        self.assertEqual(brief.status, "ready")
        self.assertEqual(brief.duration_ms, 123)
        generate_patient_brief(brief.pk, str(brief.generation_id))
        generate.assert_called_once()

    @patch("consultations.tasks.generate_cards")
    def test_worker_rejects_content_changed_during_generation(self, generate):
        brief = self.brief(status="pending")
        def change_source(source):
            type(self.consultation).objects.filter(pk=self.consultation.pk).update(notes="Nouveau texte")
            return self.cards, 50, "test-model"
        generate.side_effect = change_source
        generate_patient_brief(brief.pk, str(brief.generation_id))
        brief.refresh_from_db()
        self.assertEqual(brief.error_code, "source_changed")
        self.assertEqual(brief.status, "failed")

    def test_missing_and_invented_sources_fail_validation(self):
        self.cards[0]["sources"][0]["quote"] = "Citation inexistante"
        with self.assertRaises(BriefError):
            validate_cards(self.cards, source_data(self.consultation))
        self.cards[0]["sources"] = []
        with self.assertRaises(BriefError):
            validate_cards(self.cards, source_data(self.consultation))

    @patch("consultations.ai._post")
    def test_provider_success_sends_only_source_fields_and_keeps_key_server_side(self, post):
        post.return_value = Mock(status_code=200)
        post.return_value.json.return_value = {"stop_reason": "end_turn", "content": [{"type": "text", "text": json.dumps({"cards": self.cards})}]}
        cards, duration, model = generate_cards(source_data(self.consultation))
        self.assertEqual(len(cards), 3)
        sent = post.call_args.kwargs
        self.assertEqual(json.loads(sent["json"]["messages"][0]["content"]), source_data(self.consultation))
        self.assertNotIn(self.patient.email, json.dumps(sent["json"]))
        self.assertEqual(model, "test-model")
        self.assertGreaterEqual(duration, 0)
        self.client.force_login(self.doctor)
        self.assertNotContains(self.client.get(self.url("brief")), "synthetic-test-key", status_code=302)

    @patch("consultations.ai._post")
    def test_provider_failures_are_classified_without_raw_response(self, post):
        for status, code in ((401, "authentication"), (403, "access"), (404, "model"), (429, "rate_limit"), (500, "unavailable")):
            post.return_value = Mock(status_code=status, text="sensitive text")
            with self.assertRaises(BriefError) as caught:
                generate_cards(source_data(self.consultation))
            self.assertEqual(caught.exception.code, code)
        post.side_effect = BriefError("timeout")
        with self.assertRaises(BriefError) as caught:
            generate_cards(source_data(self.consultation))
        self.assertEqual(caught.exception.code, "timeout")

    @patch("consultations.ai._post")
    def test_truncated_or_non_json_output_is_rejected(self, post):
        post.return_value = Mock(status_code=200)
        for payload in ({"stop_reason": "max_tokens", "content": []}, {"stop_reason": "end_turn", "content": [{"type": "text", "text": "pas du json"}]}):
            post.return_value.json.return_value = payload
            with self.assertRaises(BriefError):
                generate_cards(source_data(self.consultation))
