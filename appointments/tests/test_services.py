from datetime import timedelta
from unittest import mock

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from accounts.models import DoctorProfile
from appointments import services
from appointments.models import Appointment
from core.models import Availability
from notifications.models import Notification

from .base import AppointmentTestCase, at, make_appointment, make_doctor


class AppointmentValidationTests(AppointmentTestCase):
    def build(self, start, **extra):
        return Appointment(
            patient=extra.pop("patient", self.patient),
            doctor=extra.pop("doctor", self.doctor),
            start=start,
            reason="Chest pain",
            **extra,
        )

    def test_valid_appointment_passes(self):
        self.build(at(3, 10)).full_clean()

    def test_past_date_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "must be in the future"):
            self.build(at(-1, 10)).full_clean()

    def test_slot_outside_availability_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "outside the doctor's availability"):
            self.build(at(3, 19)).full_clean()

    def test_slot_running_past_availability_end_is_rejected(self):
        with self.assertRaisesMessage(ValidationError, "outside"):
            self.build(at(3, 17, 45)).full_clean()

    def test_unavailable_block_is_rejected(self):
        Availability.objects.filter(doctor=self.doctor).update(is_free=False)
        with self.assertRaisesMessage(ValidationError, "outside"):
            self.build(at(3, 10)).full_clean()

    def test_unapproved_doctor_is_rejected(self):
        pending = make_doctor("pending@example.com", status=DoctorProfile.Status.PENDING_REVIEW)
        with self.assertRaisesMessage(ValidationError, "not approved"):
            self.build(at(3, 10), doctor=pending).full_clean()

    def test_double_booking_of_doctor_is_rejected(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10))
        with self.assertRaisesMessage(ValidationError, "doctor already has an appointment"):
            self.build(at(3, 10)).full_clean()

    def test_overlapping_appointment_is_rejected(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10), duration_minutes=60)
        with self.assertRaisesMessage(ValidationError, "doctor already has"):
            self.build(at(3, 10, 30)).full_clean()

    def test_patient_cannot_have_two_appointments_at_same_time(self):
        make_appointment(self.patient, self.other_doctor, at(3, 10))
        with self.assertRaisesMessage(ValidationError, "You already have an appointment"):
            self.build(at(3, 10)).full_clean()

    def test_cancelled_appointment_does_not_block_the_slot(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10), status=Appointment.Status.CANCELLED)
        self.build(at(3, 10)).full_clean()

    def test_historical_appointment_skips_booking_rules(self):
        self.build(at(-5, 10), status=Appointment.Status.COMPLETED).full_clean()

    def test_wrong_roles_are_rejected(self):
        with self.assertRaisesMessage(ValidationError, "Only patients"):
            self.build(at(3, 10), patient=self.other_doctor).full_clean()

    def test_risk_level_thresholds(self):
        appointment = self.build(at(3, 10))
        self.assertIsNone(appointment.risk_level)
        self.assertIsNone(appointment.risk_percent)
        for risk, level in [(0.1, "low"), (0.3, "medium"), (0.59, "medium"), (0.6, "high")]:
            appointment.no_show_risk = risk
            self.assertEqual(appointment.risk_level, level)
        self.assertEqual(appointment.risk_percent, 60)
        self.assertIn("Cardiology", str(self.doctor.main_specialty))
        self.assertIn("pending", str(appointment))


class FreeSlotTests(AppointmentTestCase):
    def test_slots_come_from_availability_in_30_minute_steps(self):
        Availability.objects.filter(doctor=self.doctor).delete()
        target = at(3, 0).date()
        Availability.objects.create(doctor=self.doctor, weekday=target.weekday(), start_time="09:00", end_time="10:30")
        slots = services.get_free_slots(self.doctor, days=7)
        self.assertEqual([s for s in slots if s.date() == target], [at(3, 9), at(3, 9, 30), at(3, 10)])

    def test_taken_slots_are_excluded(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10), duration_minutes=60)
        slots = services.get_free_slots(self.doctor)
        self.assertNotIn(at(3, 10), slots)
        self.assertNotIn(at(3, 10, 30), slots)
        self.assertIn(at(3, 11), slots)
        self.assertIn(at(3, 9, 30), slots)

    def test_cancelled_appointment_frees_the_slot(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10), status=Appointment.Status.CANCELLED)
        self.assertIn(at(3, 10), services.get_free_slots(self.doctor))

    def test_past_slots_are_excluded(self):
        now = at(2, 12, 10)
        slots = services.get_free_slots(self.doctor, now=now)
        self.assertTrue(all(slot > now for slot in slots))
        self.assertNotIn(at(2, 12), slots)
        self.assertIn(at(2, 12, 30), slots)

    def test_window_is_limited_to_days(self):
        slots = services.get_free_slots(self.doctor, days=2)
        self.assertTrue(all(slot < at(2, 0) for slot in slots))

    def test_exclude_appointment_for_reschedule(self):
        own = make_appointment(self.patient, self.doctor, at(3, 10))
        self.assertIn(at(3, 10), services.get_free_slots(self.doctor, exclude_appointment=own))

    def test_group_slots_by_day(self):
        grouped = services.group_slots_by_day([at(3, 9), at(3, 10), at(4, 9)])
        self.assertEqual(list(grouped.values()), [[at(3, 9), at(3, 10)], [at(4, 9)]])


class BookingServiceTests(AppointmentTestCase):
    def test_booking_creates_pending_and_notifies_doctor(self):
        with self.assertLogs("appointments.ml.predictor", "ERROR"):
            with self.captureOnCommitCallbacks(execute=True):
                appointment = services.book_appointment(self.patient, self.doctor, at(3, 10), "visio", "Follow-up")
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        note = Notification.objects.get(user=self.doctor)
        self.assertEqual(note.type, Notification.Type.APPOINTMENT)
        self.assertIn("New appointment request", note.message)
        self.assertEqual(note.link, appointment.get_absolute_url())
        # No model in tests: the risk task ran (eager) and recorded the failure.
        appointment.refresh_from_db()
        self.assertEqual(appointment.risk_status, Appointment.RiskStatus.FAILED)

    def test_booking_invalid_slot_raises_and_creates_nothing(self):
        with self.assertRaises(ValidationError):
            services.book_appointment(self.patient, self.doctor, at(3, 20), "cabinet", "Pain")
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(Notification.objects.exists())

    def test_only_patients_can_book(self):
        with self.assertRaises(PermissionDenied):
            services.book_appointment(self.admin, self.doctor, at(3, 10), "cabinet", "Pain")

    def test_race_on_unique_constraint_becomes_validation_error(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10))
        with mock.patch.object(Appointment, "full_clean"):
            with self.assertRaisesMessage(ValidationError, "just taken"):
                services.book_appointment(self.patient, self.doctor, at(3, 10), "cabinet", "Pain")

    def test_broker_failure_keeps_booking_and_marks_risk_failed(self):
        with mock.patch("appointments.tasks.compute_no_show_risk.delay", side_effect=ConnectionError("redis down")):
            with self.assertLogs("appointments.services", "ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    appointment = services.book_appointment(self.patient, self.doctor, at(3, 10), "cabinet", "Pain")
        appointment.refresh_from_db()
        self.assertEqual(appointment.risk_status, Appointment.RiskStatus.FAILED)

    def test_reschedule_moves_back_to_pending_and_notifies_doctor(self):
        appointment = make_appointment(
            self.patient, self.doctor, at(3, 10), status=Appointment.Status.CONFIRMED,
            reminder_sent=True, no_show_risk=0.5,
        )
        services.reschedule_appointment(appointment, self.patient, at(4, 11))
        appointment.refresh_from_db()
        self.assertEqual(appointment.start, at(4, 11))
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertFalse(appointment.reminder_sent)
        self.assertIsNone(appointment.no_show_risk)
        self.assertIn("moved their appointment", Notification.objects.get(user=self.doctor).message)

    def test_reschedule_to_invalid_slot_keeps_original(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10), status=Appointment.Status.CONFIRMED)
        with self.assertRaises(ValidationError):
            services.reschedule_appointment(appointment, self.patient, at(4, 22))
        self.assertEqual(appointment.start, at(3, 10))
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)

    def test_reschedule_rules(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        with self.assertRaises(PermissionDenied):
            services.reschedule_appointment(appointment, self.other_patient, at(4, 10))
        soon = make_appointment(self.patient, self.doctor, timezone.now() + timedelta(hours=5))
        with self.assertRaisesMessage(ValidationError, "24 hours"):
            services.reschedule_appointment(soon, self.patient, at(4, 10))


class StatusChangeTests(AppointmentTestCase):
    def notification_for(self, user):
        return Notification.objects.filter(user=user).latest("created_at")

    def test_confirm_notifies_patient(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        services.confirm_appointment(appointment, self.doctor)
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
        self.assertIn("confirmed your appointment", self.notification_for(self.patient).message)

    def test_reject_with_reason_notifies_patient(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        services.reject_appointment(appointment, self.doctor, "  On holiday ")
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.REJECTED)
        self.assertEqual(appointment.status_note, "On holiday")
        message = self.notification_for(self.patient).message
        self.assertIn("declined", message)
        self.assertIn("Reason: On holiday", message)

    def test_cancel_notifies_doctor(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10), status=Appointment.Status.CONFIRMED)
        services.cancel_appointment(appointment, self.patient)
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)
        self.assertIn("cancelled the appointment", self.notification_for(self.doctor).message)

    def test_cancel_refused_less_than_24h_before(self):
        appointment = make_appointment(self.patient, self.doctor, timezone.now() + timedelta(hours=23))
        with self.assertRaisesMessage(ValidationError, "24 hours"):
            services.cancel_appointment(appointment, self.patient)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)
        self.assertFalse(Notification.objects.exists())

    def test_complete_and_no_show_notify_patient(self):
        done = make_appointment(self.patient, self.doctor, at(-1, 10), status=Appointment.Status.CONFIRMED)
        services.complete_appointment(done, self.doctor)
        self.assertEqual(done.status, Appointment.Status.COMPLETED)
        self.assertIn("completed", self.notification_for(self.patient).message)

        missed = make_appointment(self.patient, self.doctor, at(-2, 10), status=Appointment.Status.CONFIRMED)
        services.mark_no_show(missed, self.doctor)
        self.assertEqual(missed.status, Appointment.Status.NO_SHOW)
        self.assertIn("marked as absent", self.notification_for(self.patient).message)
        self.assertEqual(Notification.objects.filter(user=self.patient).count(), 2)

    def test_only_the_appointment_doctor_can_change_status(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        for action in (services.confirm_appointment, services.reject_appointment):
            with self.assertRaises(PermissionDenied):
                action(appointment, self.other_doctor)
        with self.assertRaises(PermissionDenied):
            services.cancel_appointment(appointment, self.doctor)
        self.assertFalse(Notification.objects.exists())

    def test_invalid_transitions_are_refused(self):
        rejected = make_appointment(self.patient, self.doctor, at(3, 10), status=Appointment.Status.REJECTED)
        with self.assertRaisesMessage(ValidationError, "cannot be confirmed"):
            services.confirm_appointment(rejected, self.doctor)
        with self.assertRaisesMessage(ValidationError, "cannot be cancelled"):
            services.cancel_appointment(rejected, self.patient)
        future = make_appointment(self.patient, self.doctor, at(3, 11), status=Appointment.Status.CONFIRMED)
        with self.assertRaisesMessage(ValidationError, "not started yet"):
            services.complete_appointment(future, self.doctor)
        past_pending = make_appointment(self.patient, self.doctor, at(-1, 10))
        with self.assertRaisesMessage(ValidationError, "in the past"):
            services.confirm_appointment(past_pending, self.doctor)


class ReminderTests(AppointmentTestCase):
    def test_24h_reminder_sent_once_to_confirmed_only(self):
        now = timezone.now()
        due = make_appointment(self.patient, self.doctor, now + timedelta(hours=20), status=Appointment.Status.CONFIRMED, mode="visio")
        make_appointment(self.other_patient, self.doctor, now + timedelta(hours=20, minutes=30))  # pending
        make_appointment(self.other_patient, self.doctor, now + timedelta(hours=30), status=Appointment.Status.CONFIRMED)

        self.assertEqual(services.send_due_reminders(), {"reminders": 1, "early_reminders": 0})
        due.refresh_from_db()
        self.assertTrue(due.reminder_sent)
        note = Notification.objects.get(user=self.patient)
        self.assertEqual(note.type, Notification.Type.REMINDER)
        self.assertIn("video call", note.message)
        self.assertEqual(services.send_due_reminders(), {"reminders": 0, "early_reminders": 0})

    def test_extra_48h_reminder_for_high_risk(self):
        now = timezone.now()
        risky = make_appointment(self.patient, self.doctor, now + timedelta(hours=40), status=Appointment.Status.CONFIRMED, no_show_risk=0.8)
        make_appointment(self.other_patient, self.doctor, now + timedelta(hours=47), status=Appointment.Status.CONFIRMED, no_show_risk=0.2)

        self.assertEqual(services.send_due_reminders(), {"reminders": 0, "early_reminders": 1})
        risky.refresh_from_db()
        self.assertTrue(risky.early_reminder_sent)
        self.assertFalse(risky.reminder_sent)
        # 24h later the normal reminder still goes out.
        self.assertEqual(services.send_due_reminders(now=now + timedelta(hours=20)), {"reminders": 1, "early_reminders": 0})
        self.assertEqual(Notification.objects.filter(user=self.patient).count(), 2)
        self.assertFalse(Notification.objects.filter(user=self.other_patient).exists())
