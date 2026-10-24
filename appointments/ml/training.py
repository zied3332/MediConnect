"""Train, compare and evaluate the no-show models."""

import time

from django.utils import timezone

from .features import FEATURES

TARGET_NAMES = ["show", "no_show"]


def build_candidates(random_state=42, rf_trees=100):
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    numeric = [f for f in FEATURES if f != "weekday"]
    logistic = Pipeline([
        ("prepare", ColumnTransformer([
            ("weekday", OneHotEncoder(handle_unknown="ignore"), ["weekday"]),
            ("numeric", StandardScaler(), numeric),
        ])),
        ("classifier", LogisticRegression(class_weight="balanced", max_iter=1000)),
    ])
    forest = RandomForestClassifier(
        n_estimators=rf_trees,
        max_depth=10,
        min_samples_leaf=20,
        class_weight="balanced",
        n_jobs=-1,
        random_state=random_state,
    )
    return {"LogisticRegression": logistic, "RandomForest": forest}


def average_inference_ms(model, X, samples=200):
    """Average time to score ONE appointment, as the app does it."""
    rows = X.head(samples)
    started = time.perf_counter()
    for i in range(len(rows)):
        model.predict_proba(rows.iloc[[i]])
    return (time.perf_counter() - started) * 1000 / max(len(rows), 1)


def train_and_evaluate(X, y, random_state=42, rf_trees=100, test_size=0.2):
    """
    Stratified split, fit both candidates, keep the best F1 on the no-show
    class. Returns (best_model, metrics_dict).
    """
    from sklearn.metrics import classification_report, confusion_matrix, f1_score, roc_auc_score
    from sklearn.model_selection import train_test_split

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )

    candidates = {}
    for name, model in build_candidates(random_state, rf_trees).items():
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        candidates[name] = {
            "model": model,
            "f1_no_show": float(f1_score(y_test, predicted, pos_label=1)),
            "roc_auc": float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])),
        }

    best_name = max(candidates, key=lambda n: candidates[n]["f1_no_show"])
    best = candidates[best_name]["model"]
    if hasattr(best, "n_jobs"):
        best.set_params(n_jobs=1)  # one row at a time in the app: no thread pool overhead

    predicted = best.predict(X_test)
    metrics = {
        "trained_at": timezone.now().isoformat(timespec="seconds"),
        "chosen_model": best_name,
        "selection_metric": "F1 score of the no-show class",
        "features": FEATURES,
        "dataset": {
            "rows": int(len(X)),
            "train_rows": int(len(X_train)),
            "test_rows": int(len(X_test)),
            "no_show_rate": round(float(y.mean()), 4),
        },
        "candidates": {
            name: {"f1_no_show": round(c["f1_no_show"], 4), "roc_auc": round(c["roc_auc"], 4)}
            for name, c in candidates.items()
        },
        "classification_report": classification_report(
            y_test, predicted, target_names=TARGET_NAMES, output_dict=True, zero_division=0
        ),
        "confusion_matrix": confusion_matrix(y_test, predicted, labels=[0, 1]).tolist(),
        "roc_auc": round(candidates[best_name]["roc_auc"], 4),
        "avg_inference_ms": round(average_inference_ms(best, X_test), 3),
    }
    return best, metrics
