from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .context_processors import unread_notifications
from .models import Notification
from .services import notify, unread_count

User = get_user_model()


class NotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="ann@example.com", username="ann", password="StrongPassword123!",
            first_name="Ann", last_name="Lee", role=User.Role.PATIENT,
        )
        cls.other = User.objects.create_user(
            email="bob@example.com", username="bob", password="StrongPassword123!", role=User.Role.DOCTOR,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_notify_creates_unread_notification(self):
        note = notify(self.user, "Hello", Notification.Type.APPOINTMENT, "/appointments/1/")
        self.assertFalse(note.is_read)
        self.assertEqual((note.type, note.link), ("appointment", "/appointments/1/"))
        self.assertIn("ann@example.com", str(note))
        self.assertEqual(notify(self.user, "System message").type, "system")
        self.assertEqual(unread_count(self.user), 2)

    def test_notify_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            notify(self.user, "Hi", "sms")

    def test_list_is_newest_first_paginated_and_private(self):
        for i in range(17):
            notify(self.user, f"Message {i}")
        notify(self.other, "Secret for Bob")
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        page = response.context["page_obj"]
        self.assertEqual(len(page), 15)
        self.assertEqual(page[0].message, "Message 16")
        self.assertNotContains(response, "Secret for Bob")
        self.assertEqual(len(self.client.get(reverse("notifications:list"), {"page": 2}).context["page_obj"]), 2)

    def test_mark_read_opens_internal_link_only(self):
        internal = notify(self.user, "Go", link="/appointments/")
        response = self.client.post(reverse("notifications:mark_read", args=[internal.pk]))
        self.assertRedirects(response, "/appointments/", fetch_redirect_response=False)
        internal.refresh_from_db()
        self.assertTrue(internal.is_read)

        external = notify(self.user, "Phishing", link="https://evil.example.com/")
        response = self.client.post(reverse("notifications:mark_read", args=[external.pk]))
        self.assertRedirects(response, reverse("notifications:list"))

    def test_mark_read_requires_post_and_ownership(self):
        theirs = notify(self.other, "Not yours")
        self.assertEqual(self.client.get(reverse("notifications:mark_read", args=[theirs.pk])).status_code, 405)
        self.assertEqual(self.client.post(reverse("notifications:mark_read", args=[theirs.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("notifications:delete", args=[theirs.pk])).status_code, 404)
        theirs.refresh_from_db()
        self.assertFalse(theirs.is_read)

    def test_mark_all_read_and_delete(self):
        notify(self.user, "One")
        two = notify(self.user, "Two")
        mine_other = notify(self.other, "Bob's")
        self.client.post(reverse("notifications:mark_all_read"))
        self.assertEqual(unread_count(self.user), 0)
        self.assertEqual(unread_count(self.other), 1)

        self.client.post(reverse("notifications:delete", args=[two.pk]))
        self.assertFalse(Notification.objects.filter(pk=two.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=mine_other.pk).exists())

    def test_bell_shows_unread_count(self):
        notify(self.user, "One")
        notify(self.user, "Two")
        response = self.client.get(reverse("notifications:list"))
        self.assertContains(response, 'aria-label="Notifications, 2 unread"')
        self.assertContains(response, 'aria-live="polite"')

    def test_context_processor_for_anonymous(self):
        request = RequestFactory().get("/")
        from django.contrib.auth.models import AnonymousUser

        request.user = AnonymousUser()
        self.assertEqual(unread_notifications(request), {})
        self.assertEqual(unread_count(AnonymousUser()), 0)

    def test_login_required(self):
        self.client.logout()
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 302)
