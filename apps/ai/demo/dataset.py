"""Create-only fixtures and explicit ownership for the isolated SQLite demo."""

import sqlite3
from contextlib import closing
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management.base import CommandError
from django.db import connections, transaction

from apps.ai.configuration import require_demo_configuration

DATABASE_MARKER = "f1-ai-offline-v1"
FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "ai_demo.json"


def prepare_demo_database():
    require_demo_configuration()
    if settings.AI_MODE != "demo" or not hasattr(settings, "AI_DEMO_DATABASE_PATH"):
        raise CommandError(
            "Use --settings=config.settings.demo for offline demo setup."
        )
    database = connections["default"].settings_dict
    if database["ENGINE"] != "django.db.backends.sqlite3":
        raise CommandError("Offline demo setup requires the dedicated SQLite database.")
    path = Path(database["NAME"]).expanduser().resolve()
    if (
        path != Path(settings.AI_DEMO_DATABASE_PATH).resolve()
        or path == (settings.BASE_DIR / "db.sqlite3").resolve()
    ):
        raise CommandError(
            "Refusing to modify a database outside the configured isolated demo path."
        )
    if path.exists() and path.stat().st_size:
        try:
            with closing(
                sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
            ) as connection:
                row = connection.execute(
                    "SELECT format_version FROM ai_offline_demo_metadata WHERE id = 1"
                ).fetchone()
            if row != (DATABASE_MARKER,):
                raise sqlite3.DatabaseError("Unknown demo format")
        except sqlite3.DatabaseError:
            raise CommandError(
                "Refusing an existing unmarked SQLite database. Choose a new AI_DEMO_DB path; no data was changed."
            ) from None
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute(
                "CREATE TABLE ai_offline_demo_metadata (id INTEGER PRIMARY KEY CHECK (id = 1), format_version TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO ai_offline_demo_metadata (id, format_version) VALUES (1, ?)",
                [DATABASE_MARKER],
            )
    return path


def seed_demo_records():
    """Insert missing fixture UUIDs; never reset existing rows or conversations."""
    require_demo_configuration()
    created = 0
    with transaction.atomic():
        for record in serializers.deserialize("json", FIXTURE_PATH.read_text()):
            model = type(record.object)
            if model._default_manager.filter(pk=record.object.pk).exists():
                continue
            record.save()
            created += 1
    return created
