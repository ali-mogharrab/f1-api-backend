"""Dedicated synthetic evaluation database, separate from application data."""

from .base import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": config(
            "AI_EVALUATION_DB", default=str(BASE_DIR / "ai-evaluation.sqlite3")
        ),
    }
}
