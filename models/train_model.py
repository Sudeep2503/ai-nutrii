
"""
NutriSense AI - train_model.py (PART 1 of 4)

Append Parts 2, 3 and 4 below this file when generated.
"""

import os
import json
import logging
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
)
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    ConfusionMatrixDisplay,
)

warnings.filterwarnings("ignore")

# ---------------- CONFIG ---------------- #

RANDOM_STATE = 42
TEST_SIZE = 0.20
N_ITER = 20
CV_FOLDS = 5

BASE_DIR = Path(__file__).resolve().parent
DATASET = BASE_DIR / "processed_dataset_final.csv"

MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

PLOT_DIR = BASE_DIR / "plots"
PLOT_DIR.mkdir(exist_ok=True)

TARGET = "disease_diagnosis"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("NutriSense")


def load_dataset():
    if not DATASET.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET}")

    df = pd.read_csv(DATASET)

    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET}")

    logger.info("Dataset loaded")
    logger.info("Shape: %s", df.shape)

    return df


def validate_dataset(df):
    logger.info("Checking missing values...")
    missing = df.isnull().sum().sum()
    logger.info("Total missing values: %d", missing)

    logger.info("Checking duplicates...")
    dup = df.duplicated().sum()
    logger.info("Duplicate rows: %d", dup)

    if dup:
        df.drop_duplicates(inplace=True)
        logger.info("Duplicates removed.")

    return df


def split_data(df):
    X = df.drop(columns=[TARGET])
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    joblib.dump(list(X.columns), MODEL_DIR / "feature_columns.pkl")

    logger.info("Training samples: %d", len(X_train))
    logger.info("Testing samples: %d", len(X_test))

    return X, y, X_train, X_test, y_train, y_test


def get_search_space():
    return {
        "n_estimators": [200,300,400,500,600],
        "max_depth": [10,20,30,None],
        "min_samples_split": [2,5,10],
        "min_samples_leaf": [1,2,4],
        "max_features": ["sqrt","log2"],
        "bootstrap": [True, False]
    }


def main():
    logger.info("Starting NutriSense model training")

    df = load_dataset()
    df = validate_dataset(df)

    X, y, X_train, X_test, y_train, y_test = split_data(df)

    # ----- PART 2 STARTS HERE -----

    # ---------------- RANDOM FOREST ---------------- #

    logger.info("Initializing Random Forest...")

    rf = RandomForestClassifier(
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    search_space = get_search_space()

    logger.info("Starting RandomizedSearchCV...")

    random_search = RandomizedSearchCV(
        estimator=rf,
        param_distributions=search_space,
        n_iter=N_ITER,
        cv=CV_FOLDS,
        verbose=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        scoring="accuracy"
    )

    random_search.fit(X_train, y_train)

    best_model = random_search.best_estimator_

    logger.info("=" * 60)
    logger.info("BEST PARAMETERS")
    logger.info(random_search.best_params_)
    logger.info("=" * 60)

    logger.info(
        "Best CV Accuracy: %.4f",
        random_search.best_score_
    )

    logger.info("Training final model...")

    best_model.fit(X_train, y_train)

    logger.info("Running Cross Validation...")

    cv = StratifiedKFold(
        n_splits=CV_FOLDS,
        shuffle=True,
        random_state=RANDOM_STATE
    )

    cv_scores = cross_val_score(
        best_model,
        X,
        y,
        cv=cv,
        scoring="accuracy",
        n_jobs=-1
    )

    logger.info(
        "Cross Validation Scores: %s",
        np.round(cv_scores, 4)
    )

    logger.info(
        "Mean CV Accuracy: %.4f",
        cv_scores.mean()
    )

    logger.info(
        "Std CV Accuracy: %.4f",
        cv_scores.std()
    )

    # Predictions

    y_pred = best_model.predict(X_test)
    y_prob = best_model.predict_proba(X_test)

    logger.info("Prediction completed.")

    # ----- PART 3 STARTS HERE -----

    # ---------------- EVALUATION ---------------- #

    logger.info("=" * 60)
    logger.info("MODEL EVALUATION")
    logger.info("=" * 60)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )
    recall = recall_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )
    f1 = f1_score(
        y_test,
        y_pred,
        average="weighted",
        zero_division=0
    )

    logger.info("Accuracy : %.4f", accuracy)
    logger.info("Precision: %.4f", precision)
    logger.info("Recall   : %.4f", recall)
    logger.info("F1 Score : %.4f", f1)

    report = classification_report(
        y_test,
        y_pred,
        output_dict=True,
        zero_division=0
    )

    print("\nClassification Report\n")
    print(classification_report(
        y_test,
        y_pred,
        zero_division=0
    ))

    # ---------------- CONFUSION MATRIX ---------------- #

    cm = confusion_matrix(y_test, y_pred)

    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm
    )

    fig, ax = plt.subplots(figsize=(8, 8))
    disp.plot(
        cmap="Blues",
        ax=ax,
        colorbar=False
    )

    plt.title("NutriSense AI - Confusion Matrix")
    plt.tight_layout()

    confusion_path = PLOT_DIR / "confusion_matrix.png"
    plt.savefig(confusion_path, dpi=300)
    plt.close()

    logger.info(
        "Confusion matrix saved: %s",
        confusion_path
    )

    # ---------------- FEATURE IMPORTANCE ---------------- #

    importance = pd.DataFrame({
        "Feature": X.columns,
        "Importance": best_model.feature_importances_
    })

    importance = importance.sort_values(
        by="Importance",
        ascending=False
    )

    top_features = importance.head(15)

    plt.figure(figsize=(10, 6))
    plt.barh(
        top_features["Feature"],
        top_features["Importance"]
    )
    plt.gca().invert_yaxis()
    plt.title("Top 15 Important Features")
    plt.xlabel("Importance")
    plt.tight_layout()

    feature_plot = PLOT_DIR / "feature_importance.png"
    plt.savefig(feature_plot, dpi=300)
    plt.close()

    logger.info(
        "Feature importance saved: %s",
        feature_plot
    )

    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "cross_validation_mean": float(cv_scores.mean()),
        "cross_validation_std": float(cv_scores.std()),
        "best_parameters": random_search.best_params_,
        "classification_report": report
    }

    # ----- PART 4 STARTS HERE -----

    # ---------------- SAVE METRICS ---------------- #

    metrics_path = MODEL_DIR / "model_metrics.json"

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)

    logger.info("Metrics saved: %s", metrics_path)

    # ---------------- SAVE MODEL ---------------- #

    model_path = MODEL_DIR / "nutrition_model.pkl"
    joblib.dump(best_model, model_path)

    logger.info("Model saved: %s", model_path)

    # ---------------- SAVE FEATURE IMPORTANCE CSV ---------------- #

    importance.to_csv(
        MODEL_DIR / "feature_importance.csv",
        index=False
    )

    logger.info("Feature importance CSV saved.")

    # ---------------- SAMPLE PREDICTION ---------------- #

    logger.info("Running sample prediction...")

    sample = X_test.iloc[[0]]

    sample_prediction = best_model.predict(sample)[0]
    sample_probability = best_model.predict_proba(sample)[0]

    logger.info("Predicted Class: %s", sample_prediction)

    logger.info("Prediction Probabilities:")

    for cls, prob in zip(best_model.classes_, sample_probability):
        logger.info("Class %s : %.2f%%", cls, prob * 100)

    logger.info("=" * 60)
    logger.info("NutriSense AI Training Completed Successfully")
    logger.info("=" * 60)

    return {
        "model": best_model,
        "metrics": metrics,
        "model_path": str(model_path),
        "metrics_path": str(metrics_path)
    }


if __name__ == "__main__":
    try:
        results = main()

        print("\nTraining completed successfully.")
        print(f"Model saved to: {results['model_path']}")
        print(f"Metrics saved to: {results['metrics_path']}")

    except Exception as e:
        logger.exception("Training failed.")
        raise
