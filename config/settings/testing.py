"""
SafraLog — config/settings/testing.py
Configurações exclusivas para testes automatizados.
"""

from .base import *
from .base import DATABASES

DEBUG = True  # Necessário para que allauth não bloqueie requests

# Reutiliza credenciais do .env — só muda o nome do banco de teste
DATABASES["default"]["TEST"] = {
    "NAME": DATABASES["default"].get("NAME", "safralog") + "_test",
}

# Sessions em banco — mais confiável em testes que cache
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# CRÍTICO: cookies com Secure=True não são enviados pelo test client via HTTP
# Se base.py tiver SESSION_COOKIE_SECURE = True, force_login não funciona
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "safralog-test",
    }
}

# ModelBackend primeiro — necessário para force_login funcionar
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Remove debug_toolbar e querycount
_REMOVE = {"debug_toolbar", "querycount"}

INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in _REMOVE]

MIDDLEWARE = [m for m in MIDDLEWARE if not any(token in m for token in _REMOVE)]

SILENCED_SYSTEM_CHECKS = [
    "security.W004",
    "security.W008",
    "security.W012",
    "security.W016",
    "security.W018",
]

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
