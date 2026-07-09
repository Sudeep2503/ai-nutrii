from flask import Blueprint, render_template

from routes.auth import admin_required
from utils.db import get_db, get_db_type

admin_bp = Blueprint("admin", __name__)


def _fetch_one(cursor, query, params):
    cursor.execute(query, params)
    row = cursor.fetchone()
    if row is None:
        return 0
    return row[0]


@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True) if get_db_type() != "sqlite" else db.cursor()

    totals_query = "SELECT COUNT(*) FROM users"
    assessments_query = "SELECT COUNT(*) FROM prediction_history"
    common_def_query = "SELECT prediction_label, COUNT(*) as count FROM prediction_history GROUP BY prediction_label ORDER BY count DESC LIMIT 1"
    recent_users_query = "SELECT full_name, created_at FROM users ORDER BY created_at DESC LIMIT 5"
    recent_assessments_query = "SELECT u.full_name, p.prediction_label, p.confidence, p.prediction_date FROM prediction_history p JOIN users u ON u.id = p.user_id ORDER BY p.prediction_date DESC LIMIT 5"
    trend_query = (
        "SELECT strftime('%Y-%m-%d', prediction_date) as day, COUNT(*) as total FROM prediction_history GROUP BY day ORDER BY day DESC LIMIT 7"
        if get_db_type() == "sqlite"
        else "SELECT DATE(prediction_date) as day, COUNT(*) as total FROM prediction_history GROUP BY day ORDER BY day DESC LIMIT 7"
    )

    totals = {
        "users": _fetch_one(cursor, totals_query, ()),
        "assessments": _fetch_one(cursor, assessments_query, ()),
        "predictions": _fetch_one(cursor, assessments_query, ()),
        "common_deficiency": "N/A",
    }

    cursor.execute(common_def_query)
    common_row = cursor.fetchone()
    if common_row:
        totals["common_deficiency"] = common_row["prediction_label"] if isinstance(common_row, dict) else common_row[0]

    cursor.execute(recent_users_query)
    recent_users = [dict(row) if not isinstance(row, tuple) else {"full_name": row[0], "created_at": row[1]} for row in cursor.fetchall()]

    cursor.execute(recent_assessments_query)
    recent_assessments = [dict(row) if not isinstance(row, tuple) else {"full_name": row[0], "prediction_label": row[1], "confidence": row[2], "prediction_date": row[3]} for row in cursor.fetchall()]

    cursor.execute(trend_query)
    trends = [dict(row) if not isinstance(row, tuple) else {"day": row[0], "total": row[1]} for row in cursor.fetchall()]
    trend_labels = [item["day"] for item in reversed(trends)]
    trend_values = [item["total"] for item in reversed(trends)]

    return render_template(
        "admin.html",
        totals=totals,
        recent_users=recent_users,
        recent_assessments=recent_assessments,
        trend_labels=trend_labels,
        trend_values=trend_values,
    )
