from django.conf import settings
from django.test import Client, SimpleTestCase
from django.urls import reverse
from django.utils import translation
from appointments.tests.base import AppointmentTestCase


class PreferencesTests(SimpleTestCase):
    def tearDown(self):
        translation.deactivate()

    def test_valid_preferences_persist_in_browser_cookies(self):
        response = self.client.post(reverse('core:preferences'), {'theme': 'dark', 'language': 'ar'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies['mediconnect_theme'].value, 'dark')
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'ar')
        self.assertEqual(response.cookies['mediconnect_theme']['samesite'], 'Lax')
        page = self.client.get(response.url)
        self.assertContains(page, 'lang="ar" dir="rtl" data-theme="dark"')
        self.assertNotContains(page, 'An experience that suits you.')

    def test_rejects_invalid_values_and_external_redirects(self):
        url = reverse('core:preferences')
        bad = self.client.post(url, {'theme': 'injected', 'language': 'xx'})
        self.assertEqual(bad.status_code, 200)
        self.assertNotIn('mediconnect_theme', bad.cookies)
        response = self.client.post(url, {'theme': 'light', 'language': 'en', 'next': 'https://example.org/'})
        self.assertEqual(response.url, url + '?saved=1')

    def test_saving_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('core:preferences'), {'theme': 'dark', 'language': 'fr'}).status_code, 403)

    def test_full_copy_and_javascript_catalog_in_each_language(self):
        for language in ('en', 'fr', 'ar'):
            with self.subTest(language=language), translation.override(language):
                self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
                page = self.client.get(reverse('core:preferences'))
                self.assertContains(page, translation.gettext('Choose your appearance and language. Your preferences apply across the application on this browser.'))
                login = self.client.get(reverse('accounts:login'))
                self.assertEqual(login.status_code, 200)
                self.assertContains(login, 'lang="' + language + '"')
                catalog = self.client.get(reverse('javascript-catalog'))
                self.assertEqual(catalog.status_code, 200)
                self.assertIn(b'django.catalog', catalog.content)


class RolePreferenceTests(AppointmentTestCase):
    def tearDown(self):
        translation.deactivate()

    def test_theme_and_language_follow_every_role_without_changing_layout(self):
        self.client.cookies['mediconnect_theme'] = 'dark'
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'ar'
        for user, route in ((self.patient, 'dashboard:patient_overview'), (self.doctor, 'dashboard:doctor_overview'), (self.admin, 'dashboard:admin_overview')):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'dir="rtl" data-theme="dark"')
                self.assertContains(response, reverse('core:preferences'))
                if user.role == 'patient':
                    self.assertNotContains(response, 'id="dashboard-sidebar"')
                else:
                    self.assertContains(response, 'id="dashboard-sidebar"')

    def test_patient_forms_errors_and_counts_translate(self):
        from consultations.intake_views import IntakeForm
        from core.templatetags.ui import ui_count
        for language in ('en', 'fr', 'ar'):
            with self.subTest(language=language), translation.override(language):
                self.assertNotEqual(str(IntakeForm().fields['complaint'].label), '')
                form = IntakeForm({'complaint': 'x', 'consent': True})
                self.assertFalse(form.is_valid())
                if language == 'ar':
                    self.assertNotIn('Ensure this value', str(form.errors))
                    self.assertIn('الأطباء', ui_count(4, 'doctor'))
                elif language == 'fr':
                    self.assertEqual(ui_count(2, 'doctor'), '2 médecins')
                else:
                    self.assertEqual(ui_count(1, 'doctor'), '1 doctor')

    def test_clinical_record_text_remains_in_its_original_language(self):
        from appointments.tests.base import make_appointment, at
        from appointments.models import Appointment
        from consultations.models import Consultation
        appointment = make_appointment(self.patient, self.doctor, at(-1), status=Appointment.Status.COMPLETED)
        report = Consultation.objects.create(appointment=appointment, diagnostic='Original demonstration report', notes='Texte personnel à conserver.')
        self.client.force_login(self.patient)
        for language in ('en', 'fr', 'ar'):
            with self.subTest(language=language):
                self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
                page = self.client.get(reverse('consultations:detail', args=[report.pk]))
                self.assertContains(page, report.diagnostic)
                self.assertContains(page, report.notes)
