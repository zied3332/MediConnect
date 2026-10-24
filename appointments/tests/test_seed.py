from io import StringIO

from django.core.management import call_command

from appointments.models import Appointment
from notifications.models import Notification

from .base import AppointmentTestCase


class SeedCommandTests(AppointmentTestCase):
    def test_seed_creates_every_status_and_can_run_twice(self):
        for _ in range(2):
            out = StringIO()
            with self.assertLogs("appointments.ml.predictor", "ERROR"):  # no model in tests
                call_command("seed_appointments", stdout=out)
        demo = Appointment.objects.filter(doctor__email__endswith="@mediconnect.demo")
        self.assertEqual(set(demo.values_list("status", flat=True)), set(Appointment.Status.values))
        self.assertEqual(demo.count(), 16)
        self.assertTrue(Notification.objects.filter(type=Notification.Type.REMINDER).exists())
        self.assertIn("admin@mediconnect.demo", out.getvalue())
        self.assertIn("Demo1234!", out.getvalue())
