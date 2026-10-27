from django.urls import reverse
from appointments.tests.base import AppointmentTestCase


class PatientWebLayoutTests(AppointmentTestCase):
    def test_patient_pages_use_site_navigation_without_sidebar(self):
        self.client.force_login(self.patient)
        routes = ('dashboard:patient_overview', 'dashboard:patient_doctors', 'consultations:list',
                  'consultations:inbox', 'consultations:reviews', 'consultations:intake', 'dashboard:profile')
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'class="pw-navbar"')
                self.assertNotContains(response, 'id="dashboard-sidebar"')
                self.assertNotContains(response, 'class="mc-dashboard-topbar"')
                for destination in ('consultations:reviews', 'consultations:inbox', 'consultations:intake', 'dashboard:profile'):
                    self.assertContains(response, reverse(destination))

    def test_signed_in_patient_home_has_same_navigation(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'class="pw-navbar"')
        self.assertNotContains(response, 'id="dashboard-sidebar"')

    def test_professional_dashboards_keep_sidebar_and_topbar(self):
        for user, route in ((self.doctor, 'dashboard:doctor_overview'), (self.admin, 'dashboard:admin_overview')):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'id="dashboard-sidebar"')
                self.assertContains(response, 'class="mc-dashboard-topbar"')
                self.assertNotContains(response, 'class="pw-navbar"')
                self.assertNotContains(response, 'css/patient-site.css')

    def test_guest_home_keeps_public_navigation(self):
        response = self.client.get(reverse('core:home'))
        self.assertContains(response, 'id="hp-navigation"')
        self.assertNotContains(response, 'class="pw-navbar"')
