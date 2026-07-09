import json

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from routes.auth import get_csrf_token, login_required, validate_csrf_token
from utils.db import get_db, get_db_type

history_bp = Blueprint("history", __name__)


def _make_dict(row, cursor):
    if get_db_type() == "sqlite":
        return dict(row)
    return row


@history_bp.route("/history")
@login_required
def history():
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "date_desc")
    filter_label = request.args.get("filter_label", "")

    db = get_db()
    cursor = db.cursor(dictionary=True) if get_db_type() != "sqlite" else db.cursor()

    base_query = "SELECT * FROM prediction_history WHERE user_id = %s"
    params = [session["user_id"]]
    if get_db_type() == "sqlite":
        base_query = "SELECT * FROM prediction_history WHERE user_id = ?"

    if filter_label:
        base_query += " AND prediction_label LIKE %s" if get_db_type() != "sqlite" else " AND prediction_label LIKE ?"
        params.append(f"%{filter_label}%")

    if search:
        base_query += " AND (prediction_label LIKE %s OR prediction_date LIKE %s)" if get_db_type() != "sqlite" else " AND (prediction_label LIKE ? OR prediction_date LIKE ? )"
        params.extend([f"%{search}%", f"%{search}%"])

    order_clause = "ORDER BY prediction_date DESC"
    if sort == "date_asc":
        order_clause = "ORDER BY prediction_date ASC"
    elif sort == "confidence_desc":
        order_clause = "ORDER BY confidence DESC"
    elif sort == "confidence_asc":
        order_clause = "ORDER BY confidence ASC"

    query = f"{base_query} {order_clause} LIMIT 100"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    history = [dict(row) if get_db_type() == "sqlite" else row for row in rows]

    return render_template(
        "history.html",
        history=history,
        search=search,
        sort=sort,
        filter_label=filter_label,
        csrf_token=get_csrf_token(),
    )


@history_bp.route("/history/delete/<int:history_id>", methods=["POST"])
@login_required
def delete_history(history_id: int):
    if not validate_csrf_token():
        flash("Invalid security token. Please try again.", "error")
        return redirect(url_for("history.history"))

    db = get_db()
    cursor = db.cursor()
    if get_db_type() == "sqlite":
        cursor.execute("DELETE FROM prediction_history WHERE id = ? AND user_id = ?", (history_id, session["user_id"]))
    else:
        cursor.execute("DELETE FROM prediction_history WHERE id = %s AND user_id = %s", (history_id, session["user_id"]))
    db.commit()
    flash("Assessment record deleted successfully.", "success")
    return redirect(url_for("history.history"))


@history_bp.route("/history/<int:history_id>")
@login_required
def detail(history_id: int):
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
        flash("History record not found.", "error")
        return redirect(url_for("history.history"))

    if get_db_type() == "sqlite":
        record = dict(record)
    record["metadata"] = json.loads(record["metadata"] if isinstance(record["metadata"], str) else record["metadata"])
    return render_template("history_detail.html", record=record)
