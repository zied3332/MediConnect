import json
import tempfile
from datetime import timedelta
from pathlib import Path

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import DoctorProfile
from appointments.forms import slot_value
from appointments.models import Appointment
from notifications.models import Notification

from .base import AppointmentTestCase, at, make_appointment, make_doctor


class AccessTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.appointment = make_appointment(self.patient, self.doctor, at(3, 10))

    def test_login_required(self):
        for name, args in [
            ("appointments:my_list", []),
            ("appointments:book", []),
            ("appointments:detail", [self.appointment.pk]),
            ("appointments:doctor_list", []),
            ("appointments:admin_list", []),
            ("appointments:admin_ai_model", []),
        ]:
            url = reverse(name, args=args)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("accounts:login"), response["Location"])

    def test_patient_cannot_see_another_patients_appointment(self):
        self.client.force_login(self.other_patient)
        for name in ("appointments:detail", "appointments:reschedule", "appointments:cancel"):
            response = self.client.get(reverse(name, args=[self.appointment.pk]))
            self.assertEqual(response.status_code, 404, name)
        self.assertContains(
            self.client.post(reverse("appointments:cancel", args=[self.appointment.pk])),
            "Page not found",
            status_code=404,
        )
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.PENDING)

    def test_patient_cannot_open_doctor_or_admin_pages(self):
        self.client.force_login(self.patient)
        self.assertEqual(self.client.get(reverse("appointments:doctor_list")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("appointments:doctor_action", args=[self.appointment.pk, "confirm"])).status_code,
            403,
        )
        self.assertEqual(self.client.get(reverse("appointments:admin_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("appointments:admin_ai_model")).status_code, 403)

    def test_doctor_cannot_book_or_open_admin_pages(self):
        self.client.force_login(self.doctor)
        self.assertEqual(self.client.get(reverse("appointments:book")).status_code, 403)
        self.assertEqual(self.client.get(reverse("appointments:admin_list")).status_code, 403)

    def test_detail_visible_to_owner_doctor_and_admin_only(self):
        url = reverse("appointments:detail", args=[self.appointment.pk])
        for user, status in [(self.patient, 200), (self.doctor, 200), (self.admin, 200), (self.other_doctor, 404)]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, status, user.email)

    def test_unapproved_doctor_is_sent_to_status_page(self):
        pending = make_doctor("pending@example.com", status=DoctorProfile.Status.PENDING_REVIEW)
        self.client.force_login(pending)
        for url in (reverse("appointments:doctor_list"), reverse("appointments:detail", args=[self.appointment.pk])):
            self.assertRedirects(self.client.get(url), reverse("accounts:doctor_status"), fetch_redirect_response=False)


class PatientPagesTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.patient)

    def test_list_tabs(self):
        upcoming = make_appointment(self.patient, self.doctor, at(3, 10), status=Appointment.Status.CONFIRMED)
        past = make_appointment(self.patient, self.doctor, at(-3, 10), status=Appointment.Status.COMPLETED)
        make_appointment(self.other_patient, self.doctor, at(4, 10))

        response = self.client.get(reverse("appointments:my_list"))
        self.assertEqual(list(response.context["page_obj"]), [upcoming])
        self.assertContains(response, "mc-status--confirmed")

        response = self.client.get(reverse("appointments:my_list"), {"tab": "past"})
        self.assertEqual(list(response.context["page_obj"]), [past])
        self.assertContains(response, "Completed")

    def test_booking_flow_lists_only_approved_doctors_of_specialty(self):
        make_doctor("pending@example.com", status=DoctorProfile.Status.PENDING_REVIEW, specialty=self.specialty)
        self.assertEqual(self.client.get(reverse("appointments:book")).status_code, 200)
        response = self.client.get(reverse("appointments:book"), {"specialty": self.specialty.pk})
        self.assertEqual(set(response.context["doctors"]), {self.doctor, self.other_doctor})

    def test_slot_page_groups_free_slots_by_day(self):
        make_appointment(self.other_patient, self.doctor, at(3, 10))
        response = self.client.get(reverse("appointments:book_slot", args=[self.doctor.pk]))
        self.assertEqual(response.status_code, 200)
        values = [s["value"] for day in response.context["days"] for s in day["slots"]]
        self.assertNotIn(slot_value(at(3, 10)), values)
        self.assertIn(slot_value(at(3, 10, 30)), values)
        self.assertContains(response, 'type="radio" name="slot"')

    def test_cannot_book_unapproved_doctor(self):
        pending = make_doctor("pending@example.com", status=DoctorProfile.Status.PENDING_REVIEW)
        self.assertEqual(self.client.get(reverse("appointments:book_slot", args=[pending.pk])).status_code, 404)

    def test_book_creates_pending_appointment(self):
        response = self.client.post(
            reverse("appointments:book_slot", args=[self.doctor.pk]),
            {"slot": slot_value(at(3, 10)), "mode": "visio", "reason": "Chest pain"},
        )
        appointment = Appointment.objects.get()
        self.assertRedirects(response, appointment.get_absolute_url())
        self.assertEqual((appointment.patient, appointment.status, appointment.mode), (self.patient, "pending", "visio"))
        self.assertTrue(Notification.objects.filter(user=self.doctor).exists())

    def test_book_validation_errors(self):
        url = reverse("appointments:book_slot", args=[self.doctor.pk])
        response = self.client.post(url, {"mode": "cabinet", "reason": "x"})
        self.assertContains(response, "Please choose a time slot.")
        self.assertContains(response, "Please describe the reason")
        response = self.client.post(url, {"slot": slot_value(at(3, 22)), "mode": "cabinet", "reason": "Pain"})
        self.assertContains(response, "no longer available")
        self.assertFalse(Appointment.objects.exists())

    def test_book_reports_model_validation_error(self):
        make_appointment(self.patient, self.other_doctor, at(3, 10))
        response = self.client.post(
            reverse("appointments:book_slot", args=[self.doctor.pk]),
            {"slot": slot_value(at(3, 10)), "mode": "cabinet", "reason": "Pain"},
        )
        self.assertContains(response, "You already have an appointment at this time.")

    def test_reschedule(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10), status=Appointment.Status.CONFIRMED)
        url = reverse("appointments:reschedule", args=[appointment.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(slot_value(at(3, 10)), [s["value"] for d in response.context["days"] for s in d["slots"]])

        response = self.client.post(url, {"slot": slot_value(at(5, 14))})
        self.assertRedirects(response, appointment.get_absolute_url())
        appointment.refresh_from_db()
        self.assertEqual((appointment.start, appointment.status), (at(5, 14), Appointment.Status.PENDING))

        self.assertContains(self.client.post(url, {}), "Please choose a time slot.")

    def test_reschedule_refused_under_24h(self):
        appointment = make_appointment(self.patient, self.doctor, timezone.now() + timedelta(hours=3))
        response = self.client.get(reverse("appointments:reschedule", args=[appointment.pk]), follow=True)
        self.assertContains(response, "can no longer be changed")

    def test_cancel_confirmation_page_then_post(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        url = reverse("appointments:cancel", args=[appointment.pk])
        response = self.client.get(url)
        self.assertContains(response, "Yes, cancel the appointment")
        self.assertContains(response, "csrfmiddlewaretoken")
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Your appointment was cancelled.")
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.CANCELLED)

    def test_cancel_refused_under_24h(self):
        appointment = make_appointment(self.patient, self.doctor, timezone.now() + timedelta(hours=10))
        url = reverse("appointments:cancel", args=[appointment.pk])
        self.assertContains(self.client.get(url), "can no longer be cancelled")
        response = self.client.post(url, follow=True)
        self.assertContains(response, "more than 24 hours")
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, Appointment.Status.PENDING)


class DoctorPagesTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.doctor)

    def action(self, appointment, action, **data):
        return self.client.post(reverse("appointments:doctor_action", args=[appointment.pk, action]), data)

    def test_list_filters_and_risk_badges(self):
        high = make_appointment(self.patient, self.doctor, at(3, 10), no_show_risk=0.8, risk_status="ready")
        computing = make_appointment(self.other_patient, self.doctor, at(4, 10))
        failed = make_appointment(self.other_patient, self.doctor, at(5, 10), risk_status="failed",
                                  status=Appointment.Status.CONFIRMED)
        past = make_appointment(self.patient, self.doctor, at(-2, 10), status=Appointment.Status.COMPLETED)
        make_appointment(self.patient, self.other_doctor, at(6, 10))

        response = self.client.get(reverse("appointments:doctor_list"))
        self.assertEqual(list(response.context["page_obj"]), [high, computing, failed])
        self.assertContains(response, "High · 80%")
        self.assertContains(response, "AI estimate, you decide")
        self.assertContains(response, "Computing risk")
        self.assertContains(response, "Risk not available")

        url = reverse("appointments:doctor_list")
        self.assertEqual(list(self.client.get(url, {"when": "past"}).context["page_obj"]), [past])
        self.assertEqual(len(self.client.get(url, {"when": "all"}).context["page_obj"]), 4)
        self.assertEqual(list(self.client.get(url, {"status": "confirmed"}).context["page_obj"]), [failed])
        self.assertEqual(
            list(self.client.get(url, {"date": at(4, 0).date().isoformat()}).context["page_obj"]), [computing]
        )

    def test_confirm_reject_complete_no_show(self):
        pending = make_appointment(self.patient, self.doctor, at(3, 10))
        self.assertRedirects(self.action(pending, "confirm"), reverse("appointments:doctor_list"))
        pending.refresh_from_db()
        self.assertEqual(pending.status, Appointment.Status.CONFIRMED)

        to_reject = make_appointment(self.patient, self.doctor, at(3, 11))
        self.action(to_reject, "reject", reason="Fully booked")
        to_reject.refresh_from_db()
        self.assertEqual((to_reject.status, to_reject.status_note), ("rejected", "Fully booked"))

        done = make_appointment(self.patient, self.doctor, at(-1, 10), status=Appointment.Status.CONFIRMED)
        self.action(done, "complete")
        missed = make_appointment(self.patient, self.doctor, at(-1, 11), status=Appointment.Status.CONFIRMED)
        self.action(missed, "no-show")
        done.refresh_from_db()
        missed.refresh_from_db()
        self.assertEqual((done.status, missed.status), ("completed", "no_show"))
        self.assertEqual(Notification.objects.filter(user=self.patient).count(), 4)

    def test_cannot_act_on_another_doctors_appointment(self):
        theirs = make_appointment(self.patient, self.other_doctor, at(3, 10))
        self.assertEqual(self.action(theirs, "confirm").status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, Appointment.Status.PENDING)

    def test_invalid_action_method_and_transition(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        self.assertEqual(self.action(appointment, "explode").status_code, 404)
        url = reverse("appointments:doctor_action", args=[appointment.pk, "confirm"])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(reverse("appointments:doctor_action", args=[appointment.pk, "complete"]), follow=True)
        self.assertContains(response, "cannot be marked as completed")

    def test_next_redirect_must_be_internal(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10))
        response = self.action(appointment, "confirm", next="https://evil.example.com/")
        self.assertRedirects(response, reverse("appointments:doctor_list"))
        other = make_appointment(self.patient, self.doctor, at(3, 11))
        response = self.action(other, "confirm", next=other.get_absolute_url())
        self.assertRedirects(response, other.get_absolute_url())

    def test_retry_risk(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10), risk_status="failed")
        with self.assertLogs("appointments.ml.predictor", "ERROR"):
            with self.captureOnCommitCallbacks(execute=True):
                self.action(appointment, "retry-risk")
        appointment.refresh_from_db()
        self.assertEqual(appointment.risk_status, Appointment.RiskStatus.FAILED)  # still no model in tests

        appointment.no_show_risk = 0.4
        appointment.save()
        response = self.client.post(
            reverse("appointments:doctor_action", args=[appointment.pk, "retry-risk"]), follow=True
        )
        self.assertContains(response, "already available")

    def test_detail_shows_actions(self):
        appointment = make_appointment(self.patient, self.doctor, at(3, 10), status_note="")
        response = self.client.get(appointment.get_absolute_url())
        self.assertContains(response, "Confirm")
        self.assertContains(response, "Reason (optional)")


class AdminPagesTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin)

    def test_list_filters_and_delete(self):
        a = make_appointment(self.patient, self.doctor, at(3, 10))
        b = make_appointment(self.other_patient, self.other_doctor, at(4, 10), status=Appointment.Status.CONFIRMED)
        url = reverse("appointments:admin_list")
        self.assertEqual(len(self.client.get(url).context["page_obj"]), 2)
        self.assertEqual(list(self.client.get(url, {"doctor": self.doctor.pk}).context["page_obj"]), [a])
        self.assertEqual(list(self.client.get(url, {"patient": self.other_patient.pk}).context["page_obj"]), [b])
        self.assertEqual(list(self.client.get(url, {"status": "confirmed"}).context["page_obj"]), [b])
        self.assertEqual(list(self.client.get(url, {"date": at(3, 0).date().isoformat()}).context["page_obj"]), [a])

        response = self.client.post(reverse("appointments:admin_delete", args=[a.pk]))
        self.assertRedirects(response, url)
        self.assertFalse(Appointment.objects.filter(pk=a.pk).exists())
        self.assertEqual(self.client.get(reverse("appointments:admin_delete", args=[b.pk])).status_code, 405)

    def test_ai_page_without_metrics(self):
        with override_settings(NOSHOW_METRICS_PATH=Path(tempfile.gettempdir()) / "missing-metrics.json"):
            response = self.client.get(reverse("appointments:admin_ai_model"))
        self.assertContains(response, "Model not trained yet")

    def test_ai_page_with_metrics(self):
        metrics = {
            "trained_at": "2026-10-23T10:00:00+00:00",
            "chosen_model": "RandomForest",
            "selection_metric": "F1 score of the no-show class",
            "features": ["lead_days"],
            "dataset": {"rows": 1000, "train_rows": 800, "test_rows": 200, "no_show_rate": 0.2},
            "candidates": {"RandomForest": {"f1_no_show": 0.44, "roc_auc": 0.71},
                           "LogisticRegression": {"f1_no_show": 0.40, "roc_auc": 0.68}},
            "classification_report": {
                "show": {"precision": 0.9, "recall": 0.5, "f1-score": 0.6, "support": 160},
                "no_show": {"precision": 0.3, "recall": 0.8, "f1-score": 0.44, "support": 40},
                "accuracy": 0.55,
            },
            "confusion_matrix": [[80, 80], [8, 32]],
            "roc_auc": 0.71,
            "avg_inference_ms": 4.2,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            path.write_text(json.dumps(metrics), encoding="utf-8")
            with override_settings(NOSHOW_METRICS_PATH=path):
                response = self.client.get(reverse("appointments:admin_ai_model"))
        self.assertContains(response, "RandomForest")
        self.assertContains(response, "the doctor decides")
        self.assertEqual(response.context["confusion"], {"tn": 80, "fp": 80, "fn": 8, "tp": 32})
        self.assertEqual(len(response.context["report_rows"]), 2)

    def test_ai_page_with_broken_metrics_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metrics.json"
            path.write_text("{not json", encoding="utf-8")
            with override_settings(NOSHOW_METRICS_PATH=path), self.assertLogs("appointments.ml.predictor", "ERROR"):
                response = self.client.get(reverse("appointments:admin_ai_model"))
        self.assertContains(response, "Model not trained yet")
