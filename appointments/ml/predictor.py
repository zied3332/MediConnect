"""
Load the trained no-show model once and score appointments.

predict_risk() never raises: if the model is missing or broken it logs the
error and returns None, and the pages show "Risk not available".
"""

import json
import logging
import threading
from pathlib import Path

from django.conf import settings

from .features import FEATURES, appointment_features

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_cache = {}


def model_path():
    return Path(settings.NOSHOW_MODEL_PATH)


def metrics_path():
    return Path(settings.NOSHOW_METRICS_PATH)


def clear_cache():
    _cache.clear()


def load_model():
    """
    Return {"model": estimator, "features": [...]}; loaded from disk once and
    reloaded only when the file changes (e.g. after retraining).
    """
    import joblib

    path = model_path()
    key = (str(path), path.stat().st_mtime)  # FileNotFoundError if missing
    with _lock:
        if _cache.get("key") != key:
            bundle = joblib.load(path)
            if not isinstance(bundle, dict):
                bundle = {"model": bundle, "features": FEATURES}
            _cache["key"], _cache["bundle"] = key, bundle
        return _cache["bundle"]


def predict_risk(appointment):
    """Probability (0-1) that the patient will not show up, or None."""
    try:
        import pandas as pd

        bundle = load_model()
        features = bundle.get("features", FEATURES)
        values = appointment_features(appointment)
        row = pd.DataFrame([[values[name] for name in features]], columns=features)
        risk = float(bundle["model"].predict_proba(row)[0][1])
        return min(max(risk, 0.0), 1.0)
    except FileNotFoundError:
        logger.error(
            "No-show model not found at %s. Run: python manage.py train_noshow_model",
            model_path(),
        )
    except Exception:
        logger.exception("No-show risk prediction failed for appointment %s", getattr(appointment, "pk", None))
    return None


def load_metrics():
    """Metrics saved by train_noshow_model, or None if not trained yet."""
    try:
        with open(metrics_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        logger.exception("Could not read %s", metrics_path())
        return None
