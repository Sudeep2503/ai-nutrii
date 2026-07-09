from datetime import datetime
from typing import Any, Dict


def format_date(value: str | None) -> str:
    if not value:
        return "Not provided"
    try:
        return datetime.fromisoformat(value).strftime("%b %d, %Y")
    except ValueError:
        return value


def build_navigation(is_authenticated: bool) -> Dict[str, Any]:
    if is_authenticated:
        return {
            "items": [
                {"label": "Dashboard", "url": "/dashboard"},
                {"label": "Assessment", "url": "/assessment"},
                {"label": "History", "url": "/history"},
                {"label": "Profile", "url": "/profile"},
            ]
        }
    return {
        "items": [
            {"label": "Home", "url": "/"},
            {"label": "Login", "url": "/login"},
            {"label": "Register", "url": "/register"},
        ]
    }
