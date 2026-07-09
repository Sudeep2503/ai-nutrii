from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from routes.auth import get_csrf_token, login_required
from utils.db import get_db, get_db_type

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        if request.form.get("csrf_token", "") != session.get("csrf_token"):
            flash("Invalid security token. Please try again.", "error")
            return render_template("settings.html", csrf_token=get_csrf_token())

        theme_preference = request.form.get("theme_preference", "light")
        preferred_language = request.form.get("preferred_language", "en")
        notify_email = request.form.get("notify_email") == "on"
        notify_sms = request.form.get("notify_sms") == "on"

        db = get_db()
        cursor = db.cursor()
        if get_db_type() == "sqlite":
            cursor.execute(
                "UPDATE users SET theme_preference = ?, preferred_language = ?, notify_email = ?, notify_sms = ?, updated_at = datetime('now') WHERE id = ?",
                (theme_preference, preferred_language, int(notify_email), int(notify_sms), session["user_id"]),
            )
        else:
            cursor.execute(
                "UPDATE users SET theme_preference = %s, preferred_language = %s, notify_email = %s, notify_sms = %s, updated_at = NOW() WHERE id = %s",
                (theme_preference, preferred_language, int(notify_email), int(notify_sms), session["user_id"]),
            )
        db.commit()

        session["theme_preference"] = theme_preference
        session["preferred_language"] = preferred_language
        session["notify_email"] = notify_email
        session["notify_sms"] = notify_sms

        flash("Settings updated successfully.", "success")
        return redirect(url_for("settings.settings"))

    user_cursor = get_db().cursor()
    query = (
        "SELECT theme_preference, preferred_language, notify_email, notify_sms FROM users WHERE id = %s"
        if get_db_type() != "sqlite"
        else "SELECT theme_preference, preferred_language, notify_email, notify_sms FROM users WHERE id = ?"
    )
    user_cursor.execute(query, (session["user_id"],))
    row = user_cursor.fetchone() or ("light", "en", 1, 0)
    user_settings = {
        "theme_preference": row[0],
        "preferred_language": row[1],
        "notify_email": bool(row[2]),
        "notify_sms": bool(row[3]),
    }

    return render_template("settings.html", user_settings=user_settings, csrf_token=get_csrf_token())
