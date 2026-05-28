"""
SafraLog — config/settings/base.py
Configurações base compartilhadas entre todos os ambientes.

Hierarquia:
    base.py (este arquivo)
    ├── development.py  — DEBUG=True, toolbar, seeds
    ├── testing.py      — banco de testes, sem cache real
    └── production.py   — HTTPS, S3, Sentry, HSTS
"""

from pathlib import Path

import environ
from celery.schedules import crontab

# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# =============================================================================
# ENVIRONMENT
# =============================================================================

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    INTERNAL_IPS=(list, ["127.0.0.1"]),
)

environ.Env.read_env(BASE_DIR / ".env")

# =============================================================================
# SEGURANÇA
# =============================================================================

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# =============================================================================
# APLICAÇÕES
# =============================================================================

DJANGO_APPS = [
    "unfold",  # Admin moderno — deve vir antes do admin
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_htmx",
    "simple_history",
    "django_celery_beat",
    "django_celery_results",
    "crispy_forms",
    "crispy_tailwind",
    "django_filters",
    "import_export",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.storage",
    "health_check.contrib.celery",
    "health_check.contrib.redis",
    "django_structlog",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.tenants",
    "apps.operations",
    "apps.logistics",
    "apps.finance",
    "apps.attachments",
    "apps.reports",
    "apps.dashboard",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Third-party
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    # SafraLog
    "apps.tenants.middleware.TenantMiddleware",
    "apps.core.middleware.TimezoneMiddleware",
    "apps.core.middleware.LastSeenMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # SafraLog
                "apps.core.context_processors.app_settings",
                "apps.core.context_processors.tenant_context",
                "apps.notifications.context_processors.unread_notifications",
            ],
        },
    },
]

# =============================================================================
# BANCO DE DADOS
# =============================================================================

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://safralog:safralog@postgres:5432/safralog",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
    "options": "-c timezone=America/Sao_Paulo",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# =============================================================================
# CACHE
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://redis:6379/3"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
        },
        "KEY_PREFIX": "safralog",
        "TIMEOUT": 300,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 horas (turno de trabalho)

# =============================================================================
# AUTENTICAÇÃO
# =============================================================================

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "apps.accounts.backends.EmailOrUsernameBackend",
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# =============================================================================
# ALLAUTH
# =============================================================================
# Login por e-mail sem username.
# ACCOUNT_AUTHENTICATION_METHOD: allauth < 0.56
# ACCOUNT_LOGIN_METHODS: allauth >= 0.56 — ambos definidos para compatibilidade.

ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"  # override → "https" em production.py
ACCOUNT_SIGNUP_REDIRECT_URL = "/dashboard/"
SOCIALACCOUNT_QUERY_EMAIL = True

# =============================================================================
# INTERNACIONALIZAÇÃO
# =============================================================================

LANGUAGE_CODE = "pt-br"
TIME_ZONE = env("TIMEZONE", default="America/Sao_Paulo")
USE_I18N = True
USE_L10N = True
USE_TZ = True

# =============================================================================
# STATIC / MEDIA
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static_collected"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# =============================================================================
# UPLOADS
# =============================================================================

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB em memória
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50 MB total
FILE_UPLOAD_PERMISSIONS = 0o644
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB por arquivo

ALLOWED_UPLOAD_EXTENSIONS = [
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".txt",
    ".csv",
    ".zip",
]

# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="SafraLog <noreply@safralog.com.br>",
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# =============================================================================
# CELERY
# =============================================================================

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutos soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

CELERY_TASK_QUEUES = {
    "default": {"exchange": "default", "binding_key": "default"},
    "high_priority": {"exchange": "high_priority", "binding_key": "high_priority"},
    "low_priority": {"exchange": "low_priority", "binding_key": "low_priority"},
}
CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_BEAT_SCHEDULE = {
    # Verifica CNH vencendo em ≤30 dias — diariamente às 7h
    "check-cnh-expiry": {
        "task": "notifications.check_cnh_expiry",
        "schedule": crontab(hour=7, minute=0),
        "options": {"queue": "low_priority"},
    },
    # Verifica motoristas com saldo negativo — diariamente às 6h
    "check-negative-balances": {
        "task": "notifications.check_negative_balances",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "low_priority"},
    },
}

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": "structlog.processors.JSONRenderer",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "safralog": {
            "handlers": ["console"],  # file handler adicionado em production.py
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# THIRD-PARTY — CRISPY FORMS
# =============================================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

# =============================================================================
# THIRD-PARTY — DJANGO SIMPLE HISTORY
# =============================================================================

SIMPLE_HISTORY_REVERT_DISABLED = True
SIMPLE_HISTORY_HISTORY_CHANGE_REASON_USE_TEXT_FIELD = True

# =============================================================================
# THIRD-PARTY — UNFOLD ADMIN
# =============================================================================

UNFOLD = {
    "SITE_TITLE": "SafraLog",
    "SITE_HEADER": "SafraLog Admin",
    "SITE_URL": "/dashboard/",
    "SITE_SYMBOL": "agriculture",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "THEME": "dark",
    "COLORS": {
        "primary": {
            "50": "240 253 244",
            "100": "220 252 231",
            "200": "187 247 208",
            "300": "134 239 172",
            "400": "74 222 128",
            "500": "34 197 94",
            "600": "22 163 74",
            "700": "15 118 53",  # Verde principal SafraLog
            "800": "21 128 61",
            "900": "20 83 45",
            "950": "5 46 22",
        },
    },
}

# =============================================================================
# SAFRALOG — CONFIGURAÇÕES DO PRODUTO
# =============================================================================

APP_NAME = env("APP_NAME", default="SafraLog")
APP_VERSION = env("APP_VERSION", default="1.0.0")
APP_URL = env("APP_URL", default="http://localhost:8000")

# Precisão financeira
DECIMAL_PLACES = 4  # Preços e pesos internos
DISPLAY_DECIMAL_PLACES = 2  # Exibição ao usuário
CURRENCY = "BRL"

# =============================================================================
# SENTRY
# =============================================================================

SENTRY_DSN = env("SENTRY_DSN", default="")
