from flask import Blueprint, render_template

from routes.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "assessments": 12,
        "recommendations": 8,
        "health_score": 84,
        "active_days": 19,
    }
    recent_activity = [
        "Completed a nutrition assessment",
        "Reviewed AI guidance for protein intake",
        "Updated wellness profile",
    ]
    return render_template("dashboard.html", stats=stats, recent_activity=recent_activity)
