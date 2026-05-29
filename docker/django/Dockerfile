# =============================================================================
# SafraLog — docker/django/Dockerfile
# =============================================================================
FROM python:3.12-slim-bookworm AS base

# Variáveis de build
ARG APP_ENV=production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_HOME=/app

# Dependências de sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build
    build-essential \
    # PostgreSQL client
    libpq-dev \
    # WeasyPrint
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Imagens
    libmagic1 \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    # Node.js (Tailwind)
    nodejs \
    npm \
    # Utilitários
    curl \
    wget \
    gettext \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $APP_HOME

# =============================================================================
# STAGE: dependencies
# =============================================================================
FROM base AS dependencies

COPY requirements/ requirements/

# Instala dependências de acordo com o ambiente
RUN if [ "$APP_ENV" = "development" ]; then \
        pip install --no-cache-dir -r requirements/development.txt; \
    else \
        pip install --no-cache-dir -r requirements/production.txt; \
    fi

# =============================================================================
# STAGE: assets (Tailwind build)
# =============================================================================
FROM dependencies AS assets

COPY package.json package-lock.json* ./
COPY tailwind.config.js postcss.config.js ./
COPY static/ static/
COPY templates/ templates/

RUN npm ci --prefer-offline && npm run build

# =============================================================================
# STAGE: final
# =============================================================================
FROM dependencies AS final

# Copia código
COPY . .

# Copia assets compilados
COPY --from=assets $APP_HOME/static/css/dist/ $APP_HOME/static/css/dist/

ARG APP_ENV=production
ARG DJANGO_SECRET_KEY=build-time-placeholder
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
RUN DJANGO_SETTINGS_MODULE=$([ "$APP_ENV" = "development" ] && echo "config.settings.development" || echo "config.settings.production") \
    python manage.py collectstatic --noinput

# Configura entrypoint
COPY docker/django/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Cria usuário não-root
RUN groupadd --gid 1001 django && \
    useradd --uid 1001 --gid django --shell /bin/bash --create-home django && \
    chown -R django:django $APP_HOME /entrypoint.sh

# Volumes
RUN mkdir -p /app/media /app/static_collected /app/logs && \
    chown -R django:django /app/media /app/static_collected /app/logs

USER django

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn"]
