import json
import random
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

import joblib
import pandas as pd
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone
from sklearn.linear_model import LogisticRegression

from appointments.ml import predictor
from appointments.ml.features import FEATURES, appointment_features, dataset_features
from appointments.models import Appointment
from appointments.tasks import compute_no_show_risk, send_reminders

from .base import AppointmentTestCase, at, make_appointment


def tiny_model_file(directory):
    """Train a very small model on synthetic data and save it like the real command."""
    rng = random.Random(0)
    rows = [[rng.randint(0, 60), rng.randint(0, 5), rng.randint(0, 5), rng.randint(0, 2), rng.randint(0, 1)] for _ in range(80)]
    X = pd.DataFrame(rows, columns=FEATURES)
    y = [1 if r[0] > 30 else 0 for r in rows]
    model = LogisticRegression().fit(X, y)
    path = Path(directory) / "model.joblib"
    joblib.dump({"model": model, "features": FEATURES}, path)
    return path


def synthetic_dataset(n=300, seed=1):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        booked = pd.Timestamp("2016-04-01", tz="UTC") + pd.Timedelta(days=rng.randint(0, 30), hours=rng.randint(8, 18))
        lead = rng.randint(0, 40)
        day = (booked.normalize() + pd.Timedelta(days=lead))
        no_show = rng.random() < (0.1 + lead / 80)
        rows.append({
            "PatientId": rng.randint(1, 60),
            "AppointmentID": i,
            "ScheduledDay": booked.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "AppointmentDay": day.strftime("%Y-%m-%dT00:00:00Z"),
            "SMS_received": rng.randint(0, 1),
            "No-show": "Yes" if no_show else "No",
        })
    return pd.DataFrame(rows)


class FeatureTests(AppointmentTestCase):
    def test_appointment_features_use_only_known_history(self):
        make_appointment(self.patient, self.doctor, at(-10, 10), status=Appointment.Status.COMPLETED)
        make_appointment(self.patient, self.doctor, at(-5, 10), status=Appointment.Status.NO_SHOW)
        make_appointment(self.patient, self.doctor, at(-4, 10), status=Appointment.Status.CANCELLED)
        make_appointment(self.other_patient, self.doctor, at(-4, 11), status=Appointment.Status.NO_SHOW)
        appointment = make_appointment(self.patient, self.doctor, at(6, 10), reminder_sent=True)

        features = appointment_features(appointment)
        self.assertEqual(features["lead_days"], 6)
        self.assertEqual(features["weekday"], at(6, 10).weekday())
        self.assertEqual((features["prior_appointments"], features["prior_no_shows"]), (2, 1))
        self.assertEqual(features["reminder_sent"], 1)

    def test_dataset_features_do_not_leak_the_future(self):
        df = pd.DataFrame([
            # patient 1: no-show on Apr 5
            {"PatientId": 1, "ScheduledDay": "2016-04-01T09:00:00Z", "AppointmentDay": "2016-04-05T00:00:00Z", "SMS_received": 0, "No-show": "Yes"},
            # booked Apr 2 (before Apr 5 happened) -> history must be empty
            {"PatientId": 1, "ScheduledDay": "2016-04-02T09:00:00Z", "AppointmentDay": "2016-04-10T00:00:00Z", "SMS_received": 1, "No-show": "No"},
            # booked Apr 6 (after Apr 5) -> 1 prior appointment, 1 prior no-show
            {"PatientId": 1, "ScheduledDay": "2016-04-06T09:00:00Z", "AppointmentDay": "2016-04-08T00:00:00Z", "SMS_received": 0, "No-show": "No"},
            # another patient: no shared history
            {"PatientId": 2, "ScheduledDay": "2016-04-07T09:00:00Z", "AppointmentDay": "2016-04-07T00:00:00Z", "SMS_received": 0, "No-show": "No"},
            # booked after the appointment day: invalid row, dropped
            {"PatientId": 2, "ScheduledDay": "2016-04-09T09:00:00Z", "AppointmentDay": "2016-04-08T00:00:00Z", "SMS_received": 0, "No-show": "No"},
        ])
        X, y = dataset_features(df)
        self.assertEqual(list(X.columns), FEATURES)
        self.assertEqual(len(X), 4)
        self.assertEqual(list(y), [1, 0, 0, 0])
        self.assertEqual(list(X["lead_days"]), [4, 8, 2, 0])
        self.assertEqual(list(X["prior_appointments"]), [0, 0, 1, 0])
        self.assertEqual(list(X["prior_no_shows"]), [0, 0, 1, 0])
        self.assertEqual(list(X["reminder_sent"]), [0, 1, 0, 0])
        self.assertEqual(X["weekday"].iloc[0], 1)  # 2016-04-05 was a Tuesday

    def test_dataset_missing_columns(self):
        with self.assertRaisesMessage(ValueError, "missing columns"):
            dataset_features(pd.DataFrame({"PatientId": [1]}))


class PredictorTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.appointment = make_appointment(self.patient, self.doctor, at(20, 10))

    def test_predict_risk_with_tiny_model_is_between_0_and_1(self):
        with override_settings(NOSHOW_MODEL_PATH=tiny_model_file(self.tmp.name)):
            risk = predictor.predict_risk(self.appointment)
            self.assertIsInstance(risk, float)
            self.assertGreaterEqual(risk, 0.0)
            self.assertLessEqual(risk, 1.0)
            # Loaded once, then served from the cache.
            self.assertIs(predictor.load_model(), predictor.load_model())

    def test_raw_estimator_file_is_supported(self):
        path = tiny_model_file(self.tmp.name)
        joblib.dump(joblib.load(path)["model"], path)
        with override_settings(NOSHOW_MODEL_PATH=path):
            self.assertIsNotNone(predictor.predict_risk(self.appointment))

    def test_missing_model_returns_none(self):
        with self.assertLogs("appointments.ml.predictor", "ERROR") as logs:
            self.assertIsNone(predictor.predict_risk(self.appointment))
        self.assertIn("train_noshow_model", logs.output[0])

    def test_broken_model_returns_none(self):
        path = Path(self.tmp.name) / "model.joblib"
        path.write_bytes(b"this is not a model")
        with override_settings(NOSHOW_MODEL_PATH=path), self.assertLogs("appointments.ml.predictor", "ERROR"):
            self.assertIsNone(predictor.predict_risk(self.appointment))

    def test_task_stores_risk(self):
        with override_settings(NOSHOW_MODEL_PATH=tiny_model_file(self.tmp.name)):
            risk = compute_no_show_risk.delay(self.appointment.pk).get()
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.no_show_risk, risk)
        self.assertEqual(self.appointment.risk_status, Appointment.RiskStatus.READY)

    def test_task_marks_failure_and_ignores_unknown_ids(self):
        with self.assertLogs("appointments.ml.predictor", "ERROR"):
            self.assertIsNone(compute_no_show_risk(self.appointment.pk))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.risk_status, Appointment.RiskStatus.FAILED)
        self.assertIsNone(compute_no_show_risk(999999))

    def test_send_reminders_task(self):
        make_appointment(self.patient, self.doctor, timezone.now() + timedelta(hours=5), status=Appointment.Status.CONFIRMED)
        self.assertEqual(send_reminders.delay().get(), {"reminders": 1, "early_reminders": 0})

    def test_load_metrics(self):
        path = Path(self.tmp.name) / "metrics.json"
        path.write_text(json.dumps({"roc_auc": 0.7}), encoding="utf-8")
        with override_settings(NOSHOW_METRICS_PATH=path):
            self.assertEqual(predictor.load_metrics(), {"roc_auc": 0.7})


class TrainCommandTests(AppointmentTestCase):
    def setUp(self):
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def run_command(self, data, **options):
        out = StringIO()
        call_command(
            "train_noshow_model",
            data=str(data),
            model_out=str(self.tmp / "model.joblib"),
            metrics_out=str(self.tmp / "metrics.json"),
            rf_trees=5,
            stdout=out,
            **options,
        )
        return out.getvalue()

    def test_trains_compares_and_saves(self):
        csv = self.tmp / "noshow.csv"
        synthetic_dataset().to_csv(csv, index=False)
        output = self.run_command(csv)

        metrics = json.loads((self.tmp / "metrics.json").read_text(encoding="utf-8"))
        self.assertIn(metrics["chosen_model"], ("LogisticRegression", "RandomForest"))
        self.assertEqual(set(metrics["candidates"]), {"LogisticRegression", "RandomForest"})
        for key in ("classification_report", "confusion_matrix", "roc_auc", "avg_inference_ms", "trained_at"):
            self.assertIn(key, metrics)
        self.assertEqual(len(metrics["confusion_matrix"]), 2)
        self.assertIn("Chosen model", output)
        self.assertIn("Confusion matrix", output)

        bundle = joblib.load(self.tmp / "model.joblib")
        self.assertEqual(bundle["features"], FEATURES)
        appointment = make_appointment(self.patient, self.doctor, at(10, 10))
        with override_settings(NOSHOW_MODEL_PATH=self.tmp / "model.joblib"):
            self.assertTrue(0 <= predictor.predict_risk(appointment) <= 1)

    def test_missing_dataset_explains_where_to_download(self):
        with self.assertRaises(CommandError) as ctx:
            self.run_command(self.tmp / "nope.csv")
        self.assertIn("kaggle.com", str(ctx.exception))
        self.assertIn("appointments/ml/data/", str(ctx.exception))

    def test_wrong_file_or_single_class(self):
        bad = self.tmp / "bad.csv"
        pd.DataFrame({"a": [1, 2]}).to_csv(bad, index=False)
        with self.assertRaisesMessage(CommandError, "missing columns"):
            self.run_command(bad)

        one_class = self.tmp / "one.csv"
        df = synthetic_dataset(50)
        df["No-show"] = "No"
        df.to_csv(one_class, index=False)
        with self.assertRaisesMessage(CommandError, "at least 5"):
            self.run_command(one_class)
