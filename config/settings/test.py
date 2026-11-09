"""Isolated, network-free test defaults; never touches the development database."""

from .base import *

SECRET_KEY = "isolated-test-secret-at-least-thirty-two-characters"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
OPENAI_API_KEY = ""
