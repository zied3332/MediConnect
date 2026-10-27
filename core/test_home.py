from django.utils.translation import gettext
from django.urls import reverse
from appointments.tests.base import AppointmentTestCase, make_doctor
from accounts.models import DoctorProfile
from specialty.models import Specialty


class PublicHomeTests(AppointmentTestCase):
    def test_anonymous_home_lists_real_approved_profiles(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, gettext('Votre santé,'))
        self.assertEqual(response.context['result_count'], 2)
        self.assertContains(response, reverse('appointments:book_slot', args=[self.doctor.pk]))

    def test_pending_profiles_are_not_public(self):
        make_doctor('not-public@example.com', specialty=self.specialty, status=DoctorProfile.Status.PENDING_REVIEW)
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.context['result_count'], 2)
        self.assertNotContains(response, 'Not-public')

    def test_search_and_specialty_really_filter(self):
        response = self.client.get(reverse('core:home'), {'q': self.doctor.get_full_name()})
        self.assertEqual(list(response.context['doctors']), [self.doctor])
        other = Specialty.objects.create(name='Dermatology')
        response = self.client.get(reverse('core:home'), {'specialty': other.pk})
        self.assertEqual(response.context['result_count'], 0)
        self.assertContains(response, gettext('Aucun médecin ne correspond pour le moment.'))

    def test_invalid_specialty_and_html_input(self):
        response = self.client.get(reverse('core:home'), {'specialty': 'invalid', 'q': '<script>alert(1)</script>'})
        self.assertEqual(response.context['result_count'], 0)
        self.assertNotContains(response, '<script>alert(1)</script>')
