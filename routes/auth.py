import re
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from utils.db import get_db, get_db_type

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped(*args, **kwargs):
        if not session.get("is_admin"):
            flash("You do not have permission to view that page.", "error")
            return redirect(url_for("dashboard.dashboard"))
        return view_func(*args, **kwargs)

    return wrapped


def get_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


def validate_csrf_token() -> bool:
    submitted_token = request.form.get("csrf_token", "")
    return submitted_token and submitted_token == session.get("csrf_token")


def get_user_by_email(email: str):
    db = get_db()
    if get_db_type() == "sqlite":
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    return cursor.fetchone()


def get_user_by_id(user_id: int):
    db = get_db()
    if get_db_type() == "sqlite":
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()


def _get_stored_password_hash(user: dict):
    if not user:
        return None
    return user.get("password_hash") or user.get("password")


def is_valid_email(email: str) -> bool:
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email))


def is_strong_password(password: str) -> bool:
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
        and re.search(r"[^A-Za-z0-9]", password)
    )


def create_password_reset_token(email: str) -> str:
    token = secrets.token_urlsafe(24)
    db = get_db()
    if get_db_type() == "sqlite":
        cursor = db.cursor()
        cursor.execute("DELETE FROM password_resets WHERE email = ?", (email,))
        cursor.execute(
            "INSERT INTO password_resets (email, token, expires_at, created_at) VALUES (?, ?, ?, datetime('now'))",
            (email, token, (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")),
        )
    else:
        cursor = db.cursor()
        cursor.execute("DELETE FROM password_resets WHERE email = %s", (email,))
        cursor.execute(
            "INSERT INTO password_resets (email, token, expires_at, created_at) VALUES (%s, %s, %s, NOW())",
            (email, token, (datetime.utcnow() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")),
        )
    db.commit()
    return token


def get_reset_token(token: str):
    db = get_db()
    if get_db_type() == "sqlite":
        cursor = db.cursor()
        cursor.execute("SELECT * FROM password_resets WHERE token = ?", (token,))
        row = cursor.fetchone()
        return dict(row) if row is not None else None

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM password_resets WHERE token = %s", (token,))
    return cursor.fetchone()


def delete_reset_token(token: str):
    db = get_db()
    if get_db_type() == "sqlite":
        cursor = db.cursor()
        cursor.execute("DELETE FROM password_resets WHERE token = ?", (token,))
    else:
        cursor = db.cursor()
        cursor.execute("DELETE FROM password_resets WHERE token = %s", (token,))
    db.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Invalid security token. Please try again.", "error")
            return render_template("register.html", csrf_token=get_csrf_token())

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "Prefer not to say").strip()
        terms_accepted = request.form.get("terms") == "on"

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or not is_valid_email(email):
            errors.append("Please enter a valid email address.")
        if get_user_by_email(email):
            errors.append("Email already exists.")
        if not age.isdigit() or int(age) < 1 or int(age) > 120:
            errors.append("Please enter a valid age between 1 and 120.")
        if not is_strong_password(password):
            errors.append("Password must be at least 8 characters and include upper, lower, number, and symbol.")
        if password != confirm_password:
            errors.append("Password confirmation does not match.")
        if not terms_accepted:
            errors.append("You must accept the terms and privacy policy.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("register.html", csrf_token=get_csrf_token())

        db = get_db()
        cursor = db.cursor()
        if get_db_type() == "sqlite":
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, age, gender, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (full_name, email, generate_password_hash(password), int(age), gender),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (full_name, email, password_hash, age, gender, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (full_name, email, generate_password_hash(password), int(age), gender),
            )
        db.commit()
        flash("Registration successful. You can now sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", csrf_token=get_csrf_token())


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Invalid security token. Please try again.", "error")
            return render_template("login.html", csrf_token=get_csrf_token())

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me") == "on"

        user = get_user_by_email(email)
        stored_hash = _get_stored_password_hash(user)
        if not user or not check_password_hash(stored_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html", csrf_token=get_csrf_token())

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["full_name"]
        session["is_admin"] = bool(user.get("is_admin"))
        session["theme_preference"] = user.get("theme_preference", "light")
        session["preferred_language"] = user.get("preferred_language", "en")
        session["notify_email"] = bool(user.get("notify_email", 1))
        session["notify_sms"] = bool(user.get("notify_sms", 0))
        session.permanent = remember_me
        flash("Login successful.", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html", csrf_token=get_csrf_token())


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        if not validate_csrf_token():
            flash("Invalid security token. Please try again.", "error")
            return render_template("forgot_password.html", csrf_token=get_csrf_token())

        email = request.form.get("email", "").strip().lower()
        if not email or not is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("forgot_password.html", csrf_token=get_csrf_token())

        user = get_user_by_email(email)
        if user:
            token = create_password_reset_token(email)
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            flash("A secure password reset link has been prepared. Use the link below to continue.", "success")
            return render_template("forgot_password.html", csrf_token=get_csrf_token(), reset_link=reset_link)

        flash("If that email exists, a reset link has been prepared.", "success")
        return render_template("forgot_password.html", csrf_token=get_csrf_token())

    return render_template("forgot_password.html", csrf_token=get_csrf_token())


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    reset_entry = get_reset_token(token)
    if not reset_entry:
        flash("The password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        if not validate_csrf_token():
            flash("Invalid security token. Please try again.", "error")
            return render_template("reset_password.html", csrf_token=get_csrf_token(), token=token)

        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not is_strong_password(password):
            flash("Password must be at least 8 characters and include upper, lower, number, and symbol.", "error")
            return render_template("reset_password.html", csrf_token=get_csrf_token(), token=token)
        if password != confirm_password:
            flash("Password confirmation does not match.", "error")
            return render_template("reset_password.html", csrf_token=get_csrf_token(), token=token)

        db = get_db()
        cursor = db.cursor()
        if get_db_type() == "sqlite":
            cursor.execute(
                "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE email = ?",
                (generate_password_hash(password), reset_entry["email"]),
            )
        else:
            cursor.execute(
                "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE email = %s",
                (generate_password_hash(password), reset_entry["email"]),
            )
        db.commit()
        delete_reset_token(token)
        flash("Your password has been updated successfully.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", csrf_token=get_csrf_token(), token=token)


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_user_by_id(session["user_id"])

    if request.method == "POST":
        if not validate_csrf_token():
            flash("Invalid security token. Please try again.", "error")
            return render_template("profile.html", user=user, csrf_token=get_csrf_token())

        full_name = request.form.get("full_name", "").strip()
        age = request.form.get("age", "").strip()
        gender = request.form.get("gender", "Prefer not to say").strip()

        if not full_name:
            flash("Full name is required.", "error")
            return render_template("profile.html", user=user, csrf_token=get_csrf_token())
        if not age.isdigit() or int(age) < 1 or int(age) > 120:
            flash("Please enter a valid age between 1 and 120.", "error")
            return render_template("profile.html", user=user, csrf_token=get_csrf_token())

        db = get_db()
        cursor = db.cursor()
        if get_db_type() == "sqlite":
            cursor.execute(
                """
                UPDATE users
                SET full_name = ?, age = ?, gender = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (full_name, int(age), gender, session["user_id"]),
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET full_name = %s, age = %s, gender = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (full_name, int(age), gender, session["user_id"]),
            )
        db.commit()
        flash("Profile updated successfully.", "success")
        user = get_user_by_id(session["user_id"])

    return render_template("profile.html", user=user, csrf_token=get_csrf_token())
