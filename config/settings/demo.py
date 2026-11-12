from django.core.exceptions import ImproperlyConfigured

from .development import *

AI_MODE = "demo"
AI_DEMO_ALLOWED = True
AI_GENERATION_PROVIDER = "apps.ai.demo.providers.DemoGenerationProvider"
AI_EMBEDDING_PROVIDER = "apps.ai.demo.providers.DemoEmbeddingProvider"
AI_MODEL = "scripted-demo-v1"
AI_EMBEDDING_MODEL = "demo-token-hash-v1"
AI_EMBEDDING_DIMENSIONS = 256
OPENAI_API_KEY = "" 
RAG_MIN_SIMILARITY = 0.1
RAG_TOP_K = 4

AI_DEMO_DATABASE_PATH = (
    Path(config("AI_DEMO_DB", default=str(BASE_DIR / "ai-demo.sqlite3")))
    .expanduser()
    .resolve()
)
if AI_DEMO_DATABASE_PATH == (BASE_DIR / "db.sqlite3").resolve():
    raise ImproperlyConfigured("The offline demo cannot use the development database.")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": AI_DEMO_DATABASE_PATH,
    }
}

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "ai": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "offline-ai-demo",
    },
}
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
