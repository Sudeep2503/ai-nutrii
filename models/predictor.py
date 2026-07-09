
"""
NutriSense AI - predictor.py
Loads the trained Random Forest model and performs predictions.
"""

from pathlib import Path
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

MODEL_PATH = MODEL_DIR / "nutrition_model.pkl"
FEATURE_PATH = MODEL_DIR / "feature_columns.pkl"

_model = None
_feature_columns = None


def load_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


def load_feature_columns():
    global _feature_columns
    if _feature_columns is None:
        _feature_columns = joblib.load(FEATURE_PATH)
    return _feature_columns


def prepare_features(user_input: dict) -> pd.DataFrame:
    """
    user_input: dictionary containing feature:value pairs.
    Missing features are filled with 0.
    """
    cols = load_feature_columns()
    row = {}

    for col in cols:
        row[col] = user_input.get(col, 0)

    return pd.DataFrame([row], columns=cols)


def predict_user(user_input: dict) -> dict:
    """
    Returns:
    {
        prediction:int,
        confidence:float,
        probabilities:{class:prob}
    }
    """
    model = load_model()
    features = prepare_features(user_input)

    prediction = int(model.predict(features)[0])

    probs = model.predict_proba(features)[0]

    classes = model.classes_

    probability_dict = {
        str(int(c)): round(float(p) * 100, 2)
        for c, p in zip(classes, probs)
    }

    confidence = round(max(probability_dict.values()), 2)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "probabilities": probability_dict
    }


if __name__ == "__main__":

    sample = {
        # Replace these with real values from your Flask form
    }

    if sample:
        result = predict_user(sample)
        print(result)
    else:
        print("predictor.py loaded successfully.")
        print("Import predict_user() inside Flask.")
