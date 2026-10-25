from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.urls import reverse

from appointments.models import Appointment
from appointments.tests.base import AppointmentTestCase, at, make_appointment
from notifications.models import Notification
from .models import Consultation, Message, Avis


class ConsultationTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.appointment = make_appointment(self.patient, self.doctor, at(-1), status=Appointment.Status.COMPLETED)
        self.edit_url = reverse("consultations:edit", args=[self.appointment.pk])

    def test_doctor_creates_updates_and_notifies_patient(self):
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(self.edit_url).status_code, 200)
        response = self.client.post(self.edit_url, {"diagnostic": "Suivi", "notes": "Repos", "lien_visio": "https://meet.jit.si/demo"})
        consultation = Consultation.objects.get(appointment=self.appointment)
        self.assertRedirects(response, reverse("consultations:detail", args=[consultation.pk]))
        self.assertTrue(Notification.objects.filter(user=self.patient).exists())
        self.client.post(self.edit_url, {"diagnostic": "Suivi actualisé"})
        self.assertEqual(Consultation.objects.count(), 1)
        consultation.refresh_from_db()
        self.assertEqual(consultation.diagnostic, "Suivi actualisé")
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_patient_reads_but_cannot_write_and_strangers_cannot_read(self):
        consultation = Consultation.objects.create(appointment=self.appointment, diagnostic="Compte rendu confidentiel")
        url = reverse("consultations:detail", args=[consultation.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.patient)
        self.assertContains(self.client.get(url), "Compte rendu confidentiel")
        self.assertEqual(self.client.post(self.edit_url, {"diagnostic": "Modifié"}).status_code, 403)
        for user in (self.other_patient, self.other_doctor, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertNotContains(self.client.get(reverse("consultations:list")), "Compte rendu confidentiel")
        self.client.force_login(self.other_doctor)
        self.assertEqual(self.client.post(self.edit_url, {"diagnostic": "Modifié"}).status_code, 404)

    def test_invalid_status_diagnosis_and_url_are_rejected(self):
        self.client.force_login(self.doctor)
        for status in (Appointment.Status.PENDING, Appointment.Status.CANCELLED, Appointment.Status.REJECTED, Appointment.Status.NO_SHOW):
            self.appointment.status = status
            self.appointment.save()
            self.assertEqual(self.client.post(self.edit_url, {"diagnostic": "Test"}).status_code, 403)
            with self.assertRaises(ValidationError):
                Consultation(appointment=self.appointment, diagnostic="Test").full_clean()
        self.appointment.status = Appointment.Status.CONFIRMED
        self.appointment.save()
        for data in ({"diagnostic": ""}, {"diagnostic": "Test", "lien_visio": "javascript:alert(1)"}, {"diagnostic": "Test", "lien_visio": "http://example.com"}):
            self.assertEqual(self.client.post(self.edit_url, data).status_code, 200)
        self.assertFalse(Consultation.objects.exists())

    def test_report_prevents_appointment_deletion(self):
        Consultation.objects.create(appointment=self.appointment, diagnostic="Suivi")
        with self.assertRaises(ProtectedError):
            self.appointment.delete()
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(reverse("appointments:admin_delete", args=[self.appointment.pk])), reverse("appointments:admin_list"))
        self.assertTrue(Appointment.objects.filter(pk=self.appointment.pk).exists())


class FollowUpTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.appointment = make_appointment(self.patient, self.doctor, at(-1), status=Appointment.Status.COMPLETED)
        self.consultation = Consultation.objects.create(appointment=self.appointment, diagnostic="Démonstration")
        self.thread_url = reverse("consultations:conversation", args=[self.consultation.pk])
        self.review_url = reverse("consultations:review_edit", args=[self.consultation.pk])

    def test_conversation_send_read_reply_and_owner_only_changes(self):
        self.client.force_login(self.patient)
        response = self.client.post(self.thread_url, {"contenu": "Bonjour docteur", "auteur": self.other_patient.pk})
        self.assertRedirects(response, self.thread_url)
        message = Message.objects.get()
        self.assertEqual(message.auteur, self.patient)
        self.assertFalse(message.lu)
        self.assertTrue(Notification.objects.filter(user=self.doctor).exists())
        self.client.force_login(self.doctor)
        self.assertContains(self.client.get(self.thread_url), "Bonjour docteur")
        message.refresh_from_db()
        self.assertTrue(message.lu)
        self.assertEqual(self.client.post(reverse("consultations:message_edit", args=[message.pk]), {"contenu": "Vol"}).status_code, 404)
        self.assertEqual(self.client.post(reverse("consultations:message_delete", args=[message.pk])).status_code, 404)
        self.client.post(self.thread_url, {"contenu": "Bonjour Marie"})
        self.client.force_login(self.patient)
        self.assertContains(self.client.get(reverse("consultations:inbox")), "non lu")
        self.client.post(reverse("consultations:message_edit", args=[message.pk]), {"contenu": "Question modifiée"})
        message.refresh_from_db()
        self.assertFalse(message.lu)
        self.assertEqual(self.client.get(reverse("consultations:message_delete", args=[message.pk])).status_code, 405)
        self.client.post(reverse("consultations:message_delete", args=[message.pk]))
        self.assertFalse(Message.objects.filter(pk=message.pk).exists())

    def test_conversation_denies_other_users_and_blank_messages(self):
        for user in (self.other_patient, self.other_doctor, self.admin):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.thread_url).status_code, 404)
            self.assertEqual(self.client.post(self.thread_url, {"contenu": "Intrusion"}).status_code, 404)
        self.client.force_login(self.patient)
        for text in ("   ", "x" * 4001):
            self.assertEqual(self.client.post(self.thread_url, {"contenu": text}).status_code, 200)
        self.assertFalse(Message.objects.exists())

    def test_review_create_update_delete_and_doctor_statistics(self):
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(self.review_url).status_code, 200)
        self.client.post(self.review_url, {"note": 5, "commentaire": "Très bonne écoute", "medecin": self.other_doctor.pk})
        avis = Avis.objects.get()
        self.assertEqual(avis.medecin, self.doctor)
        self.client.post(self.review_url, {"note": 4, "commentaire": "Avis actualisé"})
        self.assertEqual(Avis.objects.count(), 1)
        self.client.force_login(self.doctor)
        response = self.client.get(reverse("consultations:reviews"))
        self.assertContains(response, "Avis actualisé")
        self.assertEqual(response.context["stats"]["average"], 4)
        self.assertEqual(self.client.post(self.review_url, {"note": 1, "commentaire": "Faux"}).status_code, 403)
        self.client.force_login(self.patient)
        self.client.post(reverse("consultations:review_delete", args=[avis.pk]))
        self.assertFalse(Avis.objects.exists())

    def test_review_requires_completed_appointment_and_valid_rating(self):
        self.client.force_login(self.patient)
        for note in (0, 6, "bad"):
            self.assertEqual(self.client.post(self.review_url, {"note": note, "commentaire": "Test"}).status_code, 200)
        self.assertFalse(Avis.objects.exists())
        self.appointment.status = Appointment.Status.CONFIRMED
        self.appointment.save()
        self.assertEqual(self.client.post(self.review_url, {"note": 5, "commentaire": "Test"}).status_code, 403)
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save()
        with self.assertRaises(ValidationError):
            Avis(consultation=self.consultation, patient=self.other_patient, medecin=self.doctor, note=5, commentaire="Test").full_clean()

    def test_admin_moderates_reviews_without_accessing_records(self):
        avis = Avis.objects.create(consultation=self.consultation, patient=self.patient, medecin=self.doctor, note=4, commentaire="Test modération")
        self.client.force_login(self.other_patient)
        self.assertEqual(self.client.post(reverse("consultations:review_delete", args=[avis.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("consultations:reviews")), "Test modération")
        self.assertEqual(self.client.get(reverse("consultations:detail", args=[self.consultation.pk])).status_code, 404)
        self.assertRedirects(self.client.post(reverse("consultations:review_delete", args=[avis.pk])), reverse("consultations:reviews"))

    def test_delete_confirmation_and_cascade_require_owning_doctor(self):
        Message.objects.create(consultation=self.consultation, auteur=self.patient, contenu="Test")
        url = reverse("consultations:delete", args=[self.consultation.pk])
        self.client.force_login(self.patient)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.other_doctor)
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Consultation.objects.exists())
        self.client.post(url)
        self.assertFalse(Consultation.objects.exists())
        self.assertFalse(Message.objects.exists())
        self.assertTrue(Appointment.objects.filter(pk=self.appointment.pk).exists())

    def test_all_pages_render_and_filters_work(self):
        for user in (self.patient, self.doctor):
            self.client.force_login(user)
            for name in ("list", "inbox", "reviews"):
                self.assertEqual(self.client.get(reverse(f"consultations:{name}")).status_code, 200)
            self.assertEqual(self.client.get(reverse("consultations:list"), {"q": "absent"}).context["page_obj"].paginator.count, 0)
            self.assertEqual(self.client.get(reverse("consultations:list"), {"status": "completed"}).context["page_obj"].paginator.count, 1)

    def test_live_consultation_search_accepts_full_name_and_returns_only_results(self):
        self.client.force_login(self.doctor)
        response = self.client.get(reverse("consultations:list"), {"q": self.patient.get_full_name()}, HTTP_X_LIVE_SEARCH="1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "data-live-count")
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.assertNotContains(response, "data-live-search")
        self.assertEqual(self.client.get(reverse("consultations:list"), {"q": "no match"}, HTTP_X_LIVE_SEARCH="1").context["page_obj"].paginator.count, 0)

    def test_live_inbox_filters_by_full_name_and_unread_without_exposing_other_users(self):
        Message.objects.create(consultation=self.consultation, auteur=self.patient, contenu="Message de suivi privé")
        self.client.force_login(self.doctor)
        response = self.client.get(reverse("consultations:inbox"), {"q": self.patient.get_full_name(), "unread": "1"}, HTTP_X_LIVE_SEARCH="1")
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "Message de suivi privé")
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.client.force_login(self.other_doctor)
        response = self.client.get(reverse("consultations:inbox"), {"q": self.patient.get_full_name()}, HTTP_X_LIVE_SEARCH="1")
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertNotContains(response, "Message de suivi privé")

    def test_search_pages_have_automatic_controls_without_filter_submit_button(self):
        self.client.force_login(self.doctor)
        for name in ("list", "inbox"):
            response = self.client.get(reverse("consultations:" + name))
            self.assertContains(response, "data-live-search")
            self.assertContains(response, "data-live-status")
            self.assertContains(response, "js/consultation-search.js")
            self.assertNotContains(response, '>Filtrer</button>')

    def test_inbox_orders_by_latest_activity_and_filters_unread_for_recipient(self):
        other_appointment = make_appointment(self.patient, self.doctor, at(-2), status=Appointment.Status.COMPLETED)
        other = Consultation.objects.create(appointment=other_appointment, diagnostic="Autre consultation")
        Message.objects.create(consultation=self.consultation, auteur=self.patient, contenu="Premier échange")
        Message.objects.create(consultation=other, auteur=self.doctor, contenu="Réponse récente")
        self.client.force_login(self.patient)
        response = self.client.get(reverse("consultations:inbox"))
        self.assertEqual(response.context["threads"][0].pk, other.pk)
        self.assertContains(response, "Réponse récente")
        response = self.client.get(reverse("consultations:inbox"), {"unread": "1"})
        self.assertEqual([item.pk for item in response.context["threads"]], [other.pk])
        self.client.get(reverse("consultations:conversation", args=[other.pk]))
        self.assertEqual(self.client.get(reverse("consultations:inbox"), {"unread": "1"}).context["page_obj"].paginator.count, 0)
        self.assertEqual(self.client.get(reverse("consultations:inbox"), {"q": "nobody"}).context["page_obj"].paginator.count, 0)

    def test_reviews_invite_only_eligible_patient_and_hide_after_submission(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("consultations:reviews"))
        self.assertContains(response, "Votre avis est attendu")
        self.assertEqual(list(response.context["eligible"]), [self.consultation])
        self.client.post(self.review_url, {"note": 5, "commentaire": "Très clair"})
        self.assertNotContains(self.client.get(reverse("consultations:reviews")), "Votre avis est attendu")
        self.client.force_login(self.other_patient)
        self.assertFalse(self.client.get(reverse("consultations:reviews")).context["eligible"].exists())
