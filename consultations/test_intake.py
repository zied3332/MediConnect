from django.utils.translation import gettext
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.tests.base import AppointmentTestCase
from .ai import BriefError
from .intake_ai import orient_patient, validate_orientation
from .intake_tasks import generate_orientation
from .intake_views import specialty_catalog
from .models import AIIntakeSession


class OrientationContractTests(SimpleTestCase):
    def setUp(self):
        self.catalog = [{'id': 1, 'name': 'Cardiology'}]
        self.result = {'specialty_id': 1, 'explanation': 'Piste à confirmer.', 'summary': 'Souhaite un suivi.', 'urgent': False}

    def test_only_catalog_identifiers(self):
        with self.assertRaises(BriefError):
            validate_orientation({**self.result, 'specialty_id': 999}, self.catalog)

    def test_null_is_supported_for_uncertainty(self):
        self.assertIsNone(validate_orientation({**self.result, 'specialty_id': None}, self.catalog)['specialty_id'])

    def test_urgency_prevents_specialty_selection(self):
        self.assertIsNone(validate_orientation({**self.result, 'urgent': True}, self.catalog)['specialty_id'])

    def test_wrong_types_and_extra_fields_rejected(self):
        for update in ({'urgent': 'false'}, {'specialty_id': True}, {'summary': ''}, {'diagnosis': 'invented'}):
            with self.subTest(update=update), self.assertRaises(BriefError):
                validate_orientation({**self.result, **update}, self.catalog)

    @override_settings(ANTHROPIC_API_KEY='test-only', ANTHROPIC_MODEL='test-model')
    @patch('consultations.intake_ai._post')
    def test_real_adapter_contract_with_mocked_transport(self, post):
        post.return_value = Mock(status_code=200, json=lambda: {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': json.dumps(self.result)}]})
        result, duration, model = orient_patient({'complaint': 'synthetic'}, self.catalog)
        self.assertEqual(result['specialty_id'], 1)
        self.assertEqual(result['summary'], 'synthetic')
        self.assertIn('confirmer par un professionnel', result['explanation'])
        self.assertGreaterEqual(duration, 0)
        self.assertEqual(model, 'test-model')

    @override_settings(ANTHROPIC_API_KEY='test-only', ANTHROPIC_MODEL='test-model')
    @patch('consultations.intake_ai._post')
    def test_provider_failure_is_sanitized(self, post):
        post.return_value = Mock(status_code=429)
        with self.assertRaises(BriefError) as caught:
            orient_patient({}, self.catalog)
        self.assertEqual(caught.exception.code, 'rate_limit')

    @override_settings(ANTHROPIC_API_KEY='test-only', ANTHROPIC_MODEL='test-model')
    @patch('consultations.intake_ai._post')
    def test_provider_outer_fence_is_accepted(self, post):
        post.return_value = Mock(status_code=200, json=lambda: {'stop_reason': 'end_turn', 'content': [{'type': 'text', 'text': '```json\n' + json.dumps(self.result) + '\n```'}]})
        self.assertEqual(orient_patient({}, self.catalog)[0]['specialty_id'], 1)


class IntakeAccessTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.patient)
        self.payload = {'complaint': 'Je souhaite une consultation de suivi fictive.', 'consent': 'True'}

    def session(self, **kwargs):
        return AIIntakeSession.objects.create(patient=self.patient, consent_at=timezone.now(), **kwargs)

    def test_page_and_authenticated_role(self):
        self.assertContains(self.client.get(reverse('consultations:intake')), gettext('Préparer mon orientation'))
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(reverse('consultations:intake')).status_code, 403)
        self.assertEqual(self.client.post(reverse('consultations:intake_start'), self.payload).status_code, 403)

    def test_no_consent_no_task(self):
        self.payload.pop('consent')
        self.assertEqual(self.client.post(reverse('consultations:intake_start'), self.payload).status_code, 400)
        self.assertFalse(AIIntakeSession.objects.exists())

    @patch('consultations.intake_tasks.orient_patient')
    def test_urgent_result_never_offers_doctors(self, orient):
        orient.return_value = ({'specialty_id': None, 'explanation': '', 'summary': '', 'urgent': True}, 10, 'test')
        session = self.session(answers={'complaint': 'Situation fictive'})
        generate_orientation(str(session.pk))
        response = self.client.get(reverse('consultations:intake_status', args=[session.pk]))
        self.assertEqual(response.json()['status'], 'urgent')
        self.assertNotIn('doctors', response.json())

    def test_single_paragraph_ui(self):
        response = self.client.get(reverse('consultations:intake'))
        self.assertContains(response, '<textarea', count=1)
        self.assertNotContains(response, 'name="duration"')
        self.assertNotContains(response, 'name="impact"')
        self.assertNotContains(response, 'name="urgent"')

    @patch('consultations.intake_tasks.generate_orientation.apply_async')
    def test_single_paragraph_persists_no_invented_answers(self, enqueue):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('consultations:intake_start'), self.payload)
        self.assertEqual(response.status_code, 202)
        self.assertEqual(AIIntakeSession.objects.get().answers, {'complaint': self.payload['complaint']})

    @patch('consultations.intake_tasks.generate_orientation.apply_async')
    def test_repeated_requests_are_not_limited(self, enqueue):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('consultations:intake_start'), self.payload)
        self.assertEqual(response.status_code, 202)
        enqueue.assert_called_once()
        for _ in range(9):
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.client.post(reverse('consultations:intake_start'), self.payload).status_code, 202)
        self.assertEqual(AIIntakeSession.objects.count(), 10)

    def test_private_status_and_delete(self):
        session = self.session()
        self.client.force_login(self.other_patient)
        self.assertEqual(self.client.get(reverse('consultations:intake_status', args=[session.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('consultations:intake_delete', args=[session.pk])).status_code, 404)
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(reverse('consultations:intake_delete', args=[session.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse('consultations:intake_delete', args=[session.pk])).status_code, 200)
        self.assertFalse(AIIntakeSession.objects.exists())

    def test_expired_job_and_no_cache(self):
        session = self.session()
        AIIntakeSession.objects.filter(pk=session.pk).update(updated_at=timezone.now()-timedelta(minutes=3))
        response = self.client.get(reverse('consultations:intake_status', args=[session.pk]))
        self.assertEqual(response.json()['status'], 'failed')
        self.assertEqual(response['Cache-Control'], 'no-store')

    @patch('consultations.intake_tasks.orient_patient')
    def test_task_result_and_doctor_eligibility(self, orient):
        orient.return_value = ({'specialty_id': self.specialty.pk, 'explanation': 'Piste.', 'summary': 'Suivi.', 'urgent': False}, 12, 'test')
        session = self.session(answers={'complaint': 'Fictif'})
        generate_orientation(str(session.pk))
        self.doctor.is_active = False
        self.doctor.save(update_fields=['is_active'])
        response = self.client.get(reverse('consultations:intake_status', args=[session.pk]))
        self.assertEqual(response.json()['status'], 'ready')
        self.assertEqual(len(response.json()['doctors']), 1)
        self.assertEqual(response.json()['duration_ms'], 12)
        self.assertEqual(specialty_catalog()[0]['id'], self.specialty.pk)

    @patch('consultations.intake_tasks.orient_patient', side_effect=BriefError('timeout'))
    def test_task_sanitizes_failure(self, orient):
        session = self.session()
        generate_orientation(str(session.pk))
        session.refresh_from_db()
        self.assertEqual(session.status, 'failed')
        self.assertEqual(session.error_code, 'timeout')

    @patch('consultations.intake_tasks.generate_orientation.apply_async', side_effect=RuntimeError('private transport detail'))
    def test_queue_unavailable_does_not_expose_exception(self, enqueue):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('consultations:intake_start'), self.payload)
        session = AIIntakeSession.objects.get()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(session.error_code, 'queue')
