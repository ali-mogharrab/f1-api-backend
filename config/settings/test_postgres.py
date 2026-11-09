"""Run the same tests against pgvector, locally or in CI."""

from .test import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("PGDATABASE", default="f1_test"),
        "USER": config("PGUSER", default="postgres"),
        "PASSWORD": config("PGPASSWORD", default="postgres"),
        "HOST": config("PGHOST", default="localhost"),
        "PORT": config("PGPORT", default="5432"),
    }
}
