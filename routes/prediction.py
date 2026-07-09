import json
import secrets
from io import BytesIO
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, session, send_file, url_for

from ai.gemini_service import GeminiService
from models.predictor import predict_user
from routes.auth import login_required
from utils.db import get_db, get_db_type
from utils.pdf_generator import generate_pdf_report

prediction_bp = Blueprint("prediction", __name__)
gemini_service = GeminiService()


def get_csrf_token() -> str:
    if "prediction_csrf_token" not in session:
        session["prediction_csrf_token"] = secrets.token_hex(16)
    return session["prediction_csrf_token"]


def validate_csrf_token() -> bool:
    submitted = request.form.get("csrf_token", "")
    return bool(submitted and submitted == session.get("prediction_csrf_token"))


def get_prediction_label(prediction_value: int) -> str:
    labels = {
        0: "Iron Deficiency",
        1: "Vitamin D Deficiency",
        2: "Vitamin B12 Deficiency",
        3: "Vitamin C Deficiency",
        4: "Calcium Deficiency",
    }
    return labels.get(int(prediction_value), f"Deficiency Class {prediction_value}")


def get_risk_level(confidence: float) -> str:
    if confidence >= 80:
        return "High"
    if confidence >= 60:
        return "Medium"
    return "Low"


def summarize_symptoms(form_data: dict) -> str:
    symptom_fields = [
        ("has_night_blindness", "Night blindness"),
        ("has_fatigue", "Fatigue"),
        ("has_bleeding_gums", "Bleeding gums"),
        ("has_bone_pain", "Bone pain"),
        ("has_muscle_weakness", "Muscle weakness"),
        ("has_numbness_tingling", "Tingling or numbness"),
        ("has_memory_problems", "Memory problems"),
        ("has_pale_skin", "Pale skin"),
    ]
    symptoms = [label for field, label in symptom_fields if form_data.get(field) == "1"]
    return ", ".join(symptoms) if symptoms else "No major symptoms reported."


def summarize_lifestyle(form_data: dict) -> str:
    lifestyle_values = {
        "Exercise": form_data.get("exercise_level", "Not provided"),
        "Diet": form_data.get("diet_type", "Not provided"),
        "Sun exposure": form_data.get("sun_exposure", "Not provided"),
        "Smoking": "Yes" if form_data.get("smoking_status") == "1" else "No",
        "Alcohol": "Yes" if form_data.get("alcohol_consumption") == "1" else "No",
        "Income level": form_data.get("income_level", "Not provided"),
        "Region": form_data.get("latitude_region", "Not provided"),
    }
    return "; ".join(f"{key}: {value}" for key, value in lifestyle_values.items())


def build_report_metadata(form_data: dict, result: dict, ai_recommendations: dict, prediction_label: str) -> dict:
    symptoms = summarize_symptoms(form_data)
    lifestyle = summarize_lifestyle(form_data)
    date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    metadata = {
        "patient_info": {
            "name": session.get("user_name", "Anonymous"),
            "age": form_data.get("age", "Not provided"),
            "gender": form_data.get("gender", "Prefer not to say"),
            "assessment_date": date,
        },
        "prediction_label": prediction_label,
        "confidence_score": round(result.get("confidence", 0), 1),
        "probabilities": result.get("probabilities", {}),
        "symptoms_summary": symptoms,
        "lifestyle_summary": lifestyle,
        "foods_to_eat": ai_recommendations.get("foods_to_eat", []),
        "foods_to_limit": ai_recommendations.get("foods_to_limit", []),
        "lifestyle_recommendations": ai_recommendations.get("lifestyle_recommendations", []),
        "ai_recommendations": ai_recommendations,
    }
    return metadata


def build_model_payload(form_data: dict) -> dict:
    age = int(form_data.get("age", 0))
    height_cm = float(form_data.get("height", 0) or 0)
    weight_kg = float(form_data.get("weight", 0) or 0)
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 2) if height_cm else 0.0

    if bmi < 18.5:
        bmi_category = 0
    elif bmi < 25:
        bmi_category = 1
    elif bmi < 30:
        bmi_category = 2
    else:
        bmi_category = 3

    if age < 18:
        age_group = 0
    elif age < 35:
        age_group = 1
    elif age < 60:
        age_group = 2
    else:
        age_group = 3

    gender_map = {"female": 0, "male": 1, "non-binary": 2, "prefer-not-to-say": 3}
    gender_value = gender_map.get(form_data.get("gender", "female").lower(), 1)

    symptom_fields = [
        "has_night_blindness",
        "has_fatigue",
        "has_bleeding_gums",
        "has_bone_pain",
        "has_muscle_weakness",
        "has_numbness_tingling",
        "has_memory_problems",
        "has_pale_skin",
    ]
    symptoms_count = sum(1 for field in symptom_fields if form_data.get(field) == "1")

    return {
        "age": age,
        "gender": gender_value,
        "bmi": bmi,
        "smoking_status": int(form_data.get("smoking_status", 0) or 0),
        "alcohol_consumption": int(form_data.get("alcohol_consumption", 0) or 0),
        "exercise_level": int(form_data.get("exercise_level", 1) or 1),
        "diet_type": int(form_data.get("diet_type", 2) or 2),
        "sun_exposure": int(form_data.get("sun_exposure", 1) or 1),
        "income_level": int(form_data.get("income_level", 1) or 1),
        "latitude_region": int(form_data.get("latitude_region", 1) or 1),
        "symptoms_count": symptoms_count,
        "has_night_blindness": 1 if form_data.get("has_night_blindness") == "1" else 0,
        "has_fatigue": 1 if form_data.get("has_fatigue") == "1" else 0,
        "has_bleeding_gums": 1 if form_data.get("has_bleeding_gums") == "1" else 0,
        "has_bone_pain": 1 if form_data.get("has_bone_pain") == "1" else 0,
        "has_muscle_weakness": 1 if form_data.get("has_muscle_weakness") == "1" else 0,
        "has_numbness_tingling": 1 if form_data.get("has_numbness_tingling") == "1" else 0,
        "has_memory_problems": 1 if form_data.get("has_memory_problems") == "1" else 0,
        "has_pale_skin": 1 if form_data.get("has_pale_skin") == "1" else 0,
        "bmi_category": bmi_category,
        "age_group": age_group,
    }


def build_ai_context(form_data: dict, result: dict, prediction_label: str) -> dict:
    symptom_fields = [
        ("has_night_blindness", "Night blindness"),
        ("has_fatigue", "Fatigue"),
        ("has_bleeding_gums", "Bleeding gums"),
        ("has_bone_pain", "Bone pain"),
        ("has_muscle_weakness", "Muscle weakness"),
        ("has_numbness_tingling", "Tingling or numbness"),
        ("has_memory_problems", "Memory problems"),
        ("has_pale_skin", "Pale skin"),
    ]
    symptoms = [label for field, label in symptom_fields if form_data.get(field) == "1"]

    return {
        "age": form_data.get("age", "Not provided"),
        "gender": form_data.get("gender", "Not provided"),
        "lifestyle": {
            "exercise_frequency": form_data.get("exercise_level", "Not provided"),
            "diet_type": form_data.get("diet_type", "Not provided"),
            "water_intake": form_data.get("water_intake", "Not provided"),
            "sun_exposure": form_data.get("sun_exposure", "Not provided"),
            "sleep_duration": form_data.get("sleep_duration", "Not provided"),
        },
        "symptoms": symptoms or ["No major symptoms reported"],
        "laboratory_values": {
            "iron_level": form_data.get("iron_level", "Not provided"),
            "vitamin_d_level": form_data.get("vitamin_d_level", "Not provided"),
            "vitamin_b12_level": form_data.get("vitamin_b12_level", "Not provided"),
            "vitamin_c_level": form_data.get("vitamin_c_level", "Not provided"),
            "calcium_level": form_data.get("calcium_level", "Not provided"),
        },
        "predicted_deficiency": prediction_label,
        "confidence_score": result.get("confidence", 0),
    }


def store_prediction(user_id: int, prediction: int, prediction_label: str, confidence: float, metadata: dict) -> int:
    db = get_db()
    cursor = db.cursor()
    metadata_text = json.dumps(metadata)
    if get_db_type() == "sqlite":
        cursor.execute(
            "INSERT INTO prediction_history (user_id, prediction, prediction_label, confidence, metadata, prediction_date) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (user_id, prediction, prediction_label, confidence, metadata_text),
        )
    else:
        cursor.execute(
            "INSERT INTO prediction_history (user_id, prediction, prediction_label, confidence, metadata, prediction_date) VALUES (%s, %s, %s, %s, %s, NOW())",
            (user_id, prediction, prediction_label, confidence, metadata_text),
        )
    db.commit()
    return cursor.lastrowid


def get_prediction_history(user_id: int, limit: int = 50):
    db = get_db()
    if get_db_type() == "sqlite":
        cursor = db.cursor()
        cursor.execute(
            "SELECT * FROM prediction_history WHERE user_id = ? ORDER BY prediction_date DESC LIMIT ?",
            (user_id, limit),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM prediction_history WHERE user_id = %s ORDER BY prediction_date DESC LIMIT %s",
        (user_id, limit),
    )
    return cursor.fetchall()


@prediction_bp.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Invalid security token. Please try again.", "error")
            return render_template("assessment.html", csrf_token=get_csrf_token())

        required_fields = ["age", "gender", "height", "weight", "exercise_level", "diet_type", "sun_exposure", "smoking_status", "alcohol_consumption", "income_level", "latitude_region"]
        errors = []
        for field in required_fields:
            value = request.form.get(field, "")
            if field in {"age", "height", "weight"}:
                try:
                    numeric_value = float(value)
                except ValueError:
                    errors.append(f"{field.replace('_', ' ').title()} must be a valid number.")
                    continue
                if field == "age" and not 1 <= numeric_value <= 120:
                    errors.append("Age must be between 1 and 120.")
                if field == "height" and not 50 <= numeric_value <= 250:
                    errors.append("Height must be between 50 and 250 cm.")
                if field == "weight" and not 20 <= numeric_value <= 300:
                    errors.append("Weight must be between 20 and 300 kg.")
            elif not value:
                errors.append(f"{field.replace('_', ' ').title()} is required.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("assessment.html", csrf_token=get_csrf_token())

        payload = build_model_payload(request.form)
        result = predict_user(payload)
        prediction_label = get_prediction_label(result["prediction"])
        ai_context = build_ai_context(request.form, result, prediction_label)
        ai_recommendations = gemini_service.get_recommendation(ai_context)
        metadata = build_report_metadata(request.form, result, ai_recommendations, prediction_label)
        prediction_id = store_prediction(
            session["user_id"],
            result["prediction"],
            prediction_label,
            result["confidence"],
            metadata,
        )

        session["latest_prediction"] = {
            "prediction_id": prediction_id,
            "prediction": result["prediction"],
            "confidence": result["confidence"],
            "probabilities": result["probabilities"],
            "ai_recommendations": ai_recommendations,
        }

        history = get_prediction_history(session["user_id"])
        return render_template(
            "result.html",
            prediction_label=prediction_label,
            risk_level=get_risk_level(result["confidence"]),
            result=result,
            history=history,
            ai_recommendations=ai_recommendations,
            csrf_token=get_csrf_token(),
        )

    return render_template("assessment.html", csrf_token=get_csrf_token())


@prediction_bp.route("/prediction")
@login_required
def prediction():
    latest_prediction = session.get("latest_prediction")
    if not latest_prediction:
        flash("Complete an assessment to view your latest prediction.", "info")
        return redirect(url_for("prediction.assessment"))

    history = get_prediction_history(session["user_id"])
    return render_template(
        "result.html",
        prediction_label=get_prediction_label(latest_prediction["prediction"]),
        risk_level=get_risk_level(latest_prediction["confidence"]),
        result={
            "prediction": latest_prediction["prediction"],
            "confidence": latest_prediction["confidence"],
            "probabilities": latest_prediction["probabilities"],
        },
        history=history,
        ai_recommendations=latest_prediction.get("ai_recommendations", {}),
        report_id=latest_prediction.get("prediction_id"),
        csrf_token=get_csrf_token(),
    )


@prediction_bp.route("/report/<int:history_id>")
@login_required
def report(history_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True) if get_db_type() != "sqlite" else db.cursor()
    query = (
        "SELECT * FROM prediction_history WHERE id = %s AND user_id = %s",
        (history_id, session["user_id"]),
    )
    if get_db_type() == "sqlite":
        query = ("SELECT * FROM prediction_history WHERE id = ? AND user_id = ?", (history_id, session["user_id"]))
    cursor.execute(*query)
    record = cursor.fetchone()
    if not record:
        flash("Report not found.", "error")
        return redirect(url_for("history.history"))

    if get_db_type() == "sqlite":
        record = dict(record)
    metadata = json.loads(record["metadata"] if isinstance(record["metadata"], str) else record["metadata"])
    return render_template(
        "report.html",
        record=record,
        metadata=metadata,
    )


@prediction_bp.route("/download-report/<int:history_id>")
@login_required
def download_report(history_id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True) if get_db_type() != "sqlite" else db.cursor()
    query = (
        "SELECT * FROM prediction_history WHERE id = %s AND user_id = %s",
        (history_id, session["user_id"]),
    )
    if get_db_type() == "sqlite":
        query = ("SELECT * FROM prediction_history WHERE id = ? AND user_id = ?", (history_id, session["user_id"]))
    cursor.execute(*query)
    record = cursor.fetchone()
    if not record:
        flash("Download could not be completed. Report not found.", "error")
        return redirect(url_for("history.history"))

    metadata = json.loads(record["metadata"] if isinstance(record["metadata"], str) else record["metadata"])
    buffer = BytesIO()
    pdf = generate_pdf_report(buffer, metadata)
    filename = f"nutrisense-report-{history_id}.pdf"
    return send_file(
        pdf,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
