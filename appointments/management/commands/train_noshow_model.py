import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from appointments.ml import predictor
from appointments.ml.features import dataset_features
from appointments.ml.training import train_and_evaluate

DOWNLOAD_HELP = (
    "Download the Kaggle dataset \"Medical Appointment No Shows\" "
    "(file KaggleV2-May-2016.csv) from "
    "https://www.kaggle.com/datasets/joniarroba/noshowappointments ,\n"
    "rename it to noshow.csv and put it in appointments/ml/data/ "
    "(or pass --data <path to the csv>)."
)


class Command(BaseCommand):
    help = "Train the appointment no-show model and save model.joblib + metrics.json."

    def add_arguments(self, parser):
        parser.add_argument("--data", default=str(settings.NOSHOW_DATASET_PATH), help="Path to the CSV dataset.")
        parser.add_argument("--model-out", default=str(settings.NOSHOW_MODEL_PATH))
        parser.add_argument("--metrics-out", default=str(settings.NOSHOW_METRICS_PATH))
        parser.add_argument("--rf-trees", type=int, default=100, help="Number of trees of the RandomForest.")
        parser.add_argument("--seed", type=int, default=42)

    def handle(self, *args, **options):
        import joblib
        import pandas as pd

        data_path = Path(options["data"])
        if not data_path.is_file():
            raise CommandError(f"Dataset not found: {data_path}\n{DOWNLOAD_HELP}")

        self.stdout.write(f"Loading {data_path} ...")
        try:
            X, y = dataset_features(pd.read_csv(data_path))
        except ValueError as error:
            raise CommandError(f"{error}\n{DOWNLOAD_HELP}")
        if y.nunique() < 2 or y.value_counts().min() < 5:
            raise CommandError("The dataset needs at least 5 shows and 5 no-shows to train.")

        self.stdout.write(f"{len(X)} appointments, no-show rate {y.mean():.1%}. Training...")
        model, metrics = train_and_evaluate(X, y, random_state=options["seed"], rf_trees=options["rf_trees"])

        model_out, metrics_out = Path(options["model_out"]), Path(options["metrics_out"])
        model_out.parent.mkdir(parents=True, exist_ok=True)
        metrics_out.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"model": model, "features": metrics["features"], "trained_at": metrics["trained_at"],
             "model_name": metrics["chosen_model"]},
            model_out,
            compress=3,
        )
        metrics_out.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        predictor.clear_cache()

        self._print(metrics)
        self.stdout.write(self.style.SUCCESS(f"Model saved to {model_out}\nMetrics saved to {metrics_out}"))

    def _print(self, m):
        out = self.stdout.write
        out("")
        out("Candidates (F1 of the no-show class on the test set):")
        for name, c in m["candidates"].items():
            out(f"  {name:<20} F1={c['f1_no_show']:.3f}  ROC-AUC={c['roc_auc']:.3f}")
        out(f"Chosen model: {m['chosen_model']}")
        out("")
        out(f"{'':<14}{'precision':>10}{'recall':>10}{'f1-score':>10}{'support':>10}")
        for label in ("show", "no_show", "macro avg", "weighted avg"):
            r = m["classification_report"][label]
            out(f"{label:<14}{r['precision']:>10.3f}{r['recall']:>10.3f}{r['f1-score']:>10.3f}{int(r['support']):>10}")
        out(f"{'accuracy':<14}{m['classification_report']['accuracy']:>30.3f}")
        (tn, fp), (fn, tp) = m["confusion_matrix"]
        out("")
        out("Confusion matrix (rows = real, columns = predicted):")
        out(f"  {'':<10}{'show':>10}{'no_show':>10}")
        out(f"  {'show':<10}{tn:>10}{fp:>10}")
        out(f"  {'no_show':<10}{fn:>10}{tp:>10}")
        out("")
        out(f"ROC-AUC: {m['roc_auc']:.3f}")
        out(f"Average inference time: {m['avg_inference_ms']:.3f} ms per appointment")
        out(f"Trained at: {m['trained_at']}")
