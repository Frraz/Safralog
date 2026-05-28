"""
SafraLog — config/settings/development.py
Configurações exclusivas de desenvolvimento local.
"""

from .base import *
from .base import LOGGING, MIDDLEWARE, env

DEBUG = True

ALLOWED_HOSTS = ["*"]
INTERNAL_IPS = [
    "127.0.0.1",
    "172.17.0.1",
]

# =============================================================================
# APPS ADICIONAIS
# =============================================================================
INSTALLED_APPS += [
    "debug_toolbar",
    "querycount",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "querycount.middleware.QueryCountMiddleware",
] + MIDDLEWARE

# =============================================================================
# SESSIONS
# =============================================================================
# Banco de dados — independente de Redis/cache.
# O allauth chama session.cycle_key() no login (proteção contra session
# fixation), invalidando a session antiga no cache → UpdateError →
# SessionInterrupted → HTTP 400. Com SESSION_ENGINE='db' isso não ocorre.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 86400  # 24h em dev

# =============================================================================
# CACHE
# =============================================================================
# LocMemCache: real (persiste na memória do processo), sem Redis externo.
# Nunca usar DummyCache com SESSION_ENGINE='cache' — descarta tudo e
# quebra o login via UpdateError.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "safralog-dev",
    }
}

# =============================================================================
# EMAIL — MailHog (http://localhost:8025)
# =============================================================================
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mailhog"
EMAIL_PORT = 1025
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""

# =============================================================================
# DJANGO DEBUG TOOLBAR
# =============================================================================
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
    "SHOW_COLLAPSED": True,
    "RESULTS_CACHE_SIZE": 100,
}

# =============================================================================
# QUERYCOUNT — Alerta de queries excessivas por request
# =============================================================================
QUERYCOUNT = {
    "THRESHOLDS": {
        "MEDIUM": 80,
        "HIGH": 150,
        "MIN_TIME_TO_LOG": 0,
        "MIN_QUERY_COUNT_TO_LOG": 5,
    },
    "IGNORE_REQUEST_PATTERNS": [
        r"^/admin/",
        r"^/health/",
        r"^/__debug__/",
        r"^/static/",
        r"^/media/",
    ],
    "IGNORE_SQL_PATTERNS": [],
    "DISPLAY_DUPLICATES": 5,
    "RESPONSE_HEADER": "X-DjangoQueryCount-Count",
}

# =============================================================================
# LOGGING — Verboso em dev
# =============================================================================
LOGGING["root"]["level"] = "INFO"

LOGGING["loggers"]["django.db.backends"] = {
    "level": "INFO",
    "handlers": ["console"],
    "propagate": False,
}

# Silencia loggers muito verbosos que poluem o terminal
for _logger in ("django.template", "django.staticfiles", "PIL", "allauth"):
    LOGGING["loggers"][_logger] = {  # type: ignore[index]
        "level": "WARNING",
        "handlers": ["console"],
        "propagate": False,
    }

# =============================================================================
# SEGURANÇA — Desabilitada intencionalmente em dev (sem HTTPS)
# =============================================================================
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# =============================================================================
# ALLAUTH
# =============================================================================
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

# =============================================================================
# SILENCIA warnings de segurança HTTPS — esperados e intencionais em dev.
# Nunca silenciar em production.py.
# =============================================================================
SILENCED_SYSTEM_CHECKS = [
    "security.W004",  # HSTS não configurado (sem HTTPS em dev)
    "security.W008",  # SECURE_SSL_REDIRECT False (sem HTTPS em dev)
    "security.W012",  # SESSION_COOKIE_SECURE False (sem HTTPS em dev)
    "security.W016",  # CSRF_COOKIE_SECURE False (sem HTTPS em dev)
    "security.W018",  # DEBUG=True (intencional em dev)
]
