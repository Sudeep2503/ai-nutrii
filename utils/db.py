import os
import sqlite3
from datetime import datetime
from typing import Optional

from flask import current_app, g
from mysql.connector import Error, connect


def get_db():
    if "db" not in g:
        try:
            g.db = connect(
                host=current_app.config["MYSQL_HOST"],
                user=current_app.config["MYSQL_USER"],
                password=current_app.config["MYSQL_PASSWORD"],
                database=current_app.config["MYSQL_DATABASE"],
                autocommit=True,
            )
            g.db_type = "mysql"
            init_mysql_schema(g.db)
        except Error:
            sqlite_path = current_app.config.get(
                "SQLITE_DB_PATH",
                os.path.join(os.path.dirname(__file__), "nutrisense.sqlite3"),
            )
            g.db = sqlite3.connect(sqlite_path)
            g.db.row_factory = sqlite3.Row
            g.db_type = "sqlite"
            init_sqlite_schema(g.db)
    return g.db


def get_db_type():
    return g.get("db_type", "mysql")


def close_db(exception=None):
    db = g.pop("db", None)
    g.pop("db_type", None)
    if db is not None:
        db.close()


def init_app_db(app):
    app.teardown_appcontext(close_db)


def _mysql_column_exists(conn, table: str, column: str) -> bool:
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM %s LIKE %s" % (table, "%s"), (column,))
    return cursor.fetchone() is not None


def _sqlite_column_exists(conn, table: str, column: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def _sqlite_rename_column(conn, table: str, old_column: str, new_column: str) -> None:
    if _sqlite_column_exists(conn, table, new_column):
        return
    if not _sqlite_column_exists(conn, table, old_column):
        return
    try:
        conn.execute(f"ALTER TABLE {table} RENAME COLUMN {old_column} TO {new_column}")
    except sqlite3.OperationalError:
        # Older SQLite versions may not support RENAME COLUMN.
        if not _sqlite_column_exists(conn, table, new_column):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {new_column} TEXT")
            conn.execute(
                f"UPDATE {table} SET {new_column} = {old_column} WHERE {old_column} IS NOT NULL"
            )


def init_mysql_schema(conn):
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(150) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            age INT NOT NULL,
            gender VARCHAR(30) NOT NULL DEFAULT 'Prefer not to say',
            is_admin BOOLEAN NOT NULL DEFAULT FALSE,
            theme_preference VARCHAR(15) NOT NULL DEFAULT 'light',
            preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
            notify_email BOOLEAN NOT NULL DEFAULT TRUE,
            notify_sms BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            token VARCHAR(255) NOT NULL UNIQUE,
            expires_at DATETIME NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            prediction INT NOT NULL,
            prediction_label VARCHAR(100) NOT NULL,
            confidence DOUBLE NOT NULL,
            metadata TEXT,
            prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    metadata_columns = [
        ("users", "is_admin", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("users", "theme_preference", "VARCHAR(15) NOT NULL DEFAULT 'light'"),
        ("users", "preferred_language", "VARCHAR(10) NOT NULL DEFAULT 'en'"),
        ("users", "notify_email", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("users", "notify_sms", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("prediction_history", "prediction_label", "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("prediction_history", "metadata", "TEXT"),
    ]
    for table, column, definition in metadata_columns:
        if not _mysql_column_exists(conn, table, column):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    conn.commit()


def _sqlite_table_exists(conn, table: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cursor.fetchone() is not None


def _sqlite_get_columns(conn, table: str):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def init_sqlite_schema(conn):
    desired_user_columns = [
        "id",
        "full_name",
        "email",
        "password_hash",
        "age",
        "gender",
        "is_admin",
        "theme_preference",
        "preferred_language",
        "notify_email",
        "notify_sms",
        "created_at",
        "updated_at",
    ]

    if _sqlite_table_exists(conn, "users"):
        existing_columns = _sqlite_get_columns(conn, "users")
        if existing_columns != desired_user_columns:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    age INTEGER NOT NULL DEFAULT 0,
                    gender TEXT DEFAULT 'Prefer not to say',
                    is_admin INTEGER DEFAULT 0,
                    theme_preference TEXT DEFAULT 'light',
                    preferred_language TEXT DEFAULT 'en',
                    notify_email INTEGER DEFAULT 1,
                    notify_sms INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            insert_columns = [
                "full_name",
                "email",
                "password_hash",
                "age",
                "gender",
                "is_admin",
                "theme_preference",
                "preferred_language",
                "notify_email",
                "notify_sms",
                "created_at",
                "updated_at",
            ]

            source_password = (
                "password_hash" if "password_hash" in existing_columns else "password"
            )
            source_age = "age" if "age" in existing_columns else None
            source_gender = "gender" if "gender" in existing_columns else None
            source_is_admin = "is_admin" if "is_admin" in existing_columns else None
            source_theme = "theme_preference" if "theme_preference" in existing_columns else None
            source_language = "preferred_language" if "preferred_language" in existing_columns else None
            source_notify_email = "notify_email" if "notify_email" in existing_columns else None
            source_notify_sms = "notify_sms" if "notify_sms" in existing_columns else None
            source_created_at = "created_at" if "created_at" in existing_columns else None
            source_updated_at = "updated_at" if "updated_at" in existing_columns else None

            select_expressions = [
                "full_name",
                "email",
                f"COALESCE({source_password}, '') AS password_hash",
                source_age or "0 AS age",
                source_gender or "'Prefer not to say' AS gender",
                source_is_admin or "0 AS is_admin",
                source_theme or "'light' AS theme_preference",
                source_language or "'en' AS preferred_language",
                source_notify_email or "1 AS notify_email",
                source_notify_sms or "0 AS notify_sms",
                source_created_at or "CURRENT_TIMESTAMP AS created_at",
                source_updated_at or "CURRENT_TIMESTAMP AS updated_at",
            ]

            conn.execute(
                f"INSERT INTO users_new ({', '.join(insert_columns)}) SELECT {', '.join(select_expressions)} FROM users"
            )
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                age INTEGER NOT NULL DEFAULT 0,
                gender TEXT DEFAULT 'Prefer not to say',
                is_admin INTEGER DEFAULT 0,
                theme_preference TEXT DEFAULT 'light',
                preferred_language TEXT DEFAULT 'en',
                notify_email INTEGER DEFAULT 1,
                notify_sms INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prediction_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            prediction INTEGER NOT NULL,
            prediction_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            metadata TEXT,
            prediction_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    schema_changes = [
        ("users", "password_hash", "TEXT"),
        ("users", "age", "INTEGER DEFAULT 0"),
        ("users", "gender", "TEXT DEFAULT 'Prefer not to say'"),
        ("users", "is_admin", "INTEGER DEFAULT 0"),
        ("users", "theme_preference", "TEXT DEFAULT 'light'"),
        ("users", "preferred_language", "TEXT DEFAULT 'en'"),
        ("users", "notify_email", "INTEGER DEFAULT 1"),
        ("users", "notify_sms", "INTEGER DEFAULT 0"),
        ("prediction_history", "prediction_label", "TEXT NOT NULL DEFAULT ''"),
        ("prediction_history", "metadata", "TEXT"),
    ]
    for table, column, definition in schema_changes:
        if not _sqlite_column_exists(conn, table, column):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    conn.commit()
