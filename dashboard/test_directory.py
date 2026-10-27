from django.urls import reverse

from appointments.tests.base import AppointmentTestCase, make_doctor
from accounts.models import DoctorProfile
from core.models import Specialty


class PatientDirectoryTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.patient)
        self.url = reverse('dashboard:patient_doctors')

    def test_directory_links_to_real_booking_and_lists_specialties(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.specialty.name)
        self.assertContains(response, reverse('appointments:book_slot', args=[self.doctor.pk]))
        self.assertEqual(response.context['page_obj'].paginator.count, 2)

    def test_unapproved_and_inactive_doctors_not_exposed(self):
        make_doctor('pending-directory@example.com', status=DoctorProfile.Status.PENDING_REVIEW, specialty=self.specialty)
        self.doctor.is_active = False
        self.doctor.save(update_fields=['is_active'])
        response = self.client.get(self.url)
        self.assertEqual(list(response.context['doctors']), [self.other_doctor])

    def test_specialty_and_name_filters_on_fragment(self):
        other = Specialty.objects.create(name='Dermatology')
        response = self.client.get(self.url, {'specialty': other.pk}, headers={'X-Live-Search': '1'})
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        self.assertNotContains(response, '<html')
        response = self.client.get(self.url, {'q': self.doctor.get_full_name()})
        self.assertEqual(list(response.context['doctors']), [self.doctor])
        self.assertEqual(self.client.get(self.url, {'specialty': 'invalid'}).context['page_obj'].paginator.count, 0)

    def test_directory_requires_patient_session(self):
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
