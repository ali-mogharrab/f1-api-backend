from pathlib import Path
from decouple import config
from datetime import timedelta


BASE_DIR = Path(__file__).resolve().parent.parent.parent


SECRET_KEY = config("SECRET_KEY", default="unsafe-development-secret-key")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda value: [host.strip() for host in value.split(",")],
)

# CORS

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    cast=lambda value: [origin.strip() for origin in value.split(",")],
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    cast=lambda value: [origin.strip() for origin in value.split(",")],
)

# forget password

FRONTEND_URL = config("FRONTEND_URL", default="http://localhost:5173")

# Email

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@f1hub.com"

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.racing",
    "apps.standings",
    "apps.content",
    "apps.ai",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Formula 1 API",
    "DESCRIPTION": (
        "A production-minded Formula 1 REST API built with Django REST Framework. "
        "Includes racing data, standings, users, favorites, and editorial content."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "DriverStatusEnum": "apps.racing.models.Driver.DriverStatus",
        "RaceStatusEnum": "apps.racing.models.Race.RaceStatus",
        "ResultStatusEnum": "apps.racing.models.RaceResult.ResultStatus",
        "ArticleStatusEnum": "apps.content.models.Article.ArticleStatus",
    },
    "SCHEMA_PATH_PREFIX": "/api/",
    "TAGS": [
        {"name": "users", "description": "Authentication, profiles, and favorites."},
        {
            "name": "racing",
            "description": "Formula 1 seasons, teams, drivers, circuits, races, and results.",
        },
        {
            "name": "standings",
            "description": "Driver and constructor championship standings.",
        },
        {
            "name": "content",
            "description": "Categories, tags, and articles/news content.",
        },
    ],
}

SIMPLE_JWT = {
    "CHECK_REVOKE_TOKEN": True,
    "TOKEN_REFRESH_SERIALIZER": "apps.users.serializers.AccountTokenRefreshSerializer",
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}

# F1 AI Analyst. Provider credentials stay on the server.
AI_MODE = "openai"
AI_ENVIRONMENT = "production"  # Fail closed for base/custom deployment settings.
AI_DEMO_ALLOWED = False
OPENAI_API_KEY = config("OPENAI_API_KEY", default="")
AI_MODEL = config("AI_MODEL", default="gpt-5-mini")
AI_EMBEDDING_MODEL = config("AI_EMBEDDING_MODEL", default="text-embedding-3-small")
AI_EMBEDDING_DIMENSIONS = config("AI_EMBEDDING_DIMENSIONS", default=1536, cast=int)
AI_GENERATION_PROVIDER = "apps.ai.providers.OpenAIProvider"
AI_EMBEDDING_PROVIDER = "apps.ai.providers.OpenAIProvider"
AI_MAX_OUTPUT_TOKENS = config("AI_MAX_OUTPUT_TOKENS", default=2000, cast=int)
AI_MAX_TOOL_CALLS = config("AI_MAX_TOOL_CALLS", default=6, cast=int)
AI_PROVIDER_TIMEOUT = config("AI_PROVIDER_TIMEOUT", default=20, cast=float)
AI_REQUEST_TIMEOUT = config("AI_REQUEST_TIMEOUT", default=90, cast=float)
AI_MESSAGE_MAX_LENGTH = 4000
AI_HISTORY_MESSAGES = 12
AI_CONTEXT_MAX_CHARS = 24000
AI_TOOL_RESULT_MAX_CHARS = 24000
AI_CONVERSATION_MAX_MESSAGES = 100
AI_THROTTLE_RATE = config("AI_THROTTLE_RATE", default="10/hour")
AUTH_THROTTLE_RATES = {
    "login": config("AUTH_LOGIN_RATE", default="10/minute"),
    "registration": config("AUTH_REGISTRATION_RATE", default="10/hour"),
    "password_reset": config("AUTH_PASSWORD_RESET_RATE", default="10/hour"),
    "token_refresh": config("AUTH_REFRESH_RATE", default="60/minute"),
}
RAG_TOP_K = config("RAG_TOP_K", default=5, cast=int)
RAG_MIN_SIMILARITY = config("RAG_MIN_SIMILARITY", default=0.3, cast=float)
RAG_CHUNK_SIZE = config("RAG_CHUNK_SIZE", default=1200, cast=int)
RAG_CHUNK_OVERLAP = config("RAG_CHUNK_OVERLAP", default=200, cast=int)
RAG_MAX_ARTICLE_CHARS = 200000
RAG_EMBEDDING_BATCH_SIZE = 32
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "ai": {
        "BACKEND": config("AI_CACHE_BACKEND", default="django.core.cache.backends.locmem.LocMemCache"),
        "LOCATION": config("AI_CACHE_LOCATION", default="f1-ai-throttle"),
    },
}
