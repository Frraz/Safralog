"""
SafraLog — config/settings/production.py
Configurações exclusivas de produção.

Herda de base.py e sobrescreve apenas o necessário.
Nunca importar diretamente — usar via DJANGO_SETTINGS_MODULE.

Checklist antes do deploy:
  [ ] DJANGO_SECRET_KEY — chave forte, nunca reutilizar
  [ ] DATABASE_URL — PostgreSQL de produção
  [ ] CELERY_BROKER_URL / CELERY_RESULT_BACKEND — Redis de produção
  [ ] SENTRY_DSN — monitoramento de erros
  [ ] STORAGE_BACKEND=s3 + credenciais AWS (ou manter local)
  [ ] ADMIN_EMAIL — recebe alertas de erro
  [ ] Certificado SSL válido (HTTPS)
"""

from __future__ import annotations

from .base import *
from .base import BASE_DIR, LOGGING, SENTRY_DSN, env

# =============================================================================
# CORE
# =============================================================================

DEBUG = False

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["safralog.com.br", "www.safralog.com.br"],
)

# =============================================================================
# SEGURANÇA — HTTPS
# =============================================================================

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)

# HSTS — instrui browsers a sempre usar HTTPS
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=31_536_000)  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# =============================================================================
# COOKIES
# =============================================================================

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False  # HTMX precisa ler o token via JS

# =============================================================================
# ALLAUTH
# =============================================================================

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

# =============================================================================
# EMAIL
# =============================================================================

ADMINS = [("SafraLog Admin", env("ADMIN_EMAIL", default="admin@safralog.com.br"))]
MANAGERS = ADMINS

# =============================================================================
# STORAGE — S3 (opcional; padrão: filesystem local)
# =============================================================================

if env("STORAGE_BACKEND", default="local") == "s3":
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="sa-east-1")
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = "private"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
    AWS_QUERYSTRING_AUTH = True  # URLs assinadas para arquivos privados
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
        },
    }

# =============================================================================
# LOGGING — adiciona file handler em produção
# =============================================================================

LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING["handlers"]["file"] = {
    "level": "WARNING",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": str(LOGS_DIR / "safralog.log"),
    "maxBytes": 10 * 1024 * 1024,  # 10 MB
    "backupCount": 5,
    "formatter": "verbose",
}

# safralog logger grava em console + file em produção
LOGGING["loggers"]["safralog"]["handlers"] = ["console", "file"]
LOGGING["root"]["level"] = "WARNING"

# =============================================================================
# SENTRY — monitoramento de erros (ativo se SENTRY_DSN configurado)
# =============================================================================

if SENTRY_DSN:
    import logging as _logging

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(monitor_beat_tasks=True),
            RedisIntegration(),
            LoggingIntegration(
                level=_logging.INFO,  # captura INFO como breadcrumbs
                event_level=_logging.ERROR,  # envia ERROR como eventos
            ),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        profiles_sample_rate=env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
        environment="production",
        release=env("APP_VERSION", default="1.0.0"),
    )
