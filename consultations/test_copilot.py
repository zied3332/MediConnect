import json
from types import SimpleNamespace
from unittest.mock import patch
from django.test import override_settings
from django.urls import reverse
from appointments.tests.base import AppointmentTestCase, make_appointment, at
from appointments.models import Appointment
from consultations.models import Consultation
from consultations.ai import BriefError
from consultations.copilot import prepare_draft


@override_settings(ANTHROPIC_API_KEY='fake-test-key', ANTHROPIC_MODEL='test-model')
class CopilotTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.appointment = make_appointment(self.patient,self.doctor,at(1),status=Appointment.Status.CONFIRMED)
        self.url=reverse('consultations:copilot',args=[self.appointment.pk])

    def response(self, groups, code=200):
        return SimpleNamespace(status_code=code,json=lambda:{'stop_reason':'end_turn','content':[{'type':'text','text':json.dumps(groups)}]})

    @patch('consultations.copilot._post')
    def test_extracts_sources_without_saving_a_report(self, provider):
        provider.return_value=self.response({'motif':['Contrôle fictif.'],'observations':[],'diagnostic':[],'suivi':['Questions à préparer.']})
        self.client.force_login(self.doctor)
        result=self.client.post(self.url,{'notes':'Contrôle fictif. Questions à préparer.','consent':'on'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['sections'][2]['text'],'')
        self.assertFalse(Consultation.objects.exists())
        sent=provider.call_args.kwargs['json']['messages'][0]['content']
        self.assertNotIn(self.patient.email,sent)
        self.assertNotIn(self.doctor.email,sent)

    @patch('consultations.copilot._post')
    def test_rejects_invented_text_and_invalid_structure(self, provider):
        for groups in ({'motif':['Prescrire un antibiotique pendant sept jours'],'observations':[],'diagnostic':[],'suivi':[]}, {'motif':[]}):
            provider.return_value=self.response(groups)
            with self.assertRaises(BriefError): prepare_draft('Notes fictives sans texte inventé.')

    @patch('consultations.copilot._post')
    def test_rejects_excerpt_that_drops_a_negation(self, provider):
        provider.return_value=self.response({'motif':[],'observations':[],'diagnostic':[],'suivi':['traitement supplémentaire prescrit']})
        with self.assertRaises(BriefError): prepare_draft('Aucun traitement supplémentaire prescrit.')

    @patch('consultations.copilot.prepare_draft')
    def test_access_is_restricted_to_appointment_doctor(self, generate):
        for user,status in ((self.patient,403),(self.admin,403),(self.other_doctor,404)):
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.url,{'notes':'Notes fictives pour la démonstration.','consent':'on'}).status_code,status)
        generate.assert_not_called()

    @patch('consultations.copilot.prepare_draft')
    def test_requires_consent_and_bounded_notes(self, generate):
        self.client.force_login(self.doctor)
        for data in ({'notes':'Notes fictives suffisamment longues.'},{'notes':'court','consent':'on'},{'notes':'x'*8001,'consent':'on'}):
            self.assertEqual(self.client.post(self.url,data).status_code,400)
        generate.assert_not_called()

    def test_replacement_entry_point_and_editor(self):
        report=Consultation.objects.create(appointment=self.appointment,diagnostic='Fiction')
        self.client.force_login(self.doctor)
        self.assertRedirects(self.client.get(reverse('consultations:brief',args=[report.pk])),reverse('consultations:edit',args=[self.appointment.pk]))
        page=self.client.get(reverse('consultations:edit',args=[self.appointment.pk]))
        self.assertContains(page,'id="copilot-input"')
        self.assertContains(page,'id="consultation-report-form"')
        self.client.force_login(self.patient)
        self.assertRedirects(self.client.get(reverse('consultations:brief',args=[report.pk])),reverse('consultations:detail',args=[report.pk]))

    @patch('consultations.copilot._post')
    def test_provider_error_is_explicit(self, provider):
        provider.return_value=self.response({},429)
        self.client.force_login(self.doctor)
        response=self.client.post(self.url,{'notes':'Notes fictives pour la démonstration.','consent':'on'})
        self.assertEqual(response.status_code,503)
        self.assertIn('error',response.json())
