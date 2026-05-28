#!/bin/bash
# =============================================================================
# SafraLog — docker/django/entrypoint.sh
# =============================================================================
set -euo pipefail

echo "🌾 SafraLog — iniciando..."
echo "   Ambiente: ${DJANGO_SETTINGS_MODULE:-config.settings.development}"

# Aguarda PostgreSQL ficar disponível
wait_for_postgres() {
    echo "⏳ Aguardando PostgreSQL..."
    local retries=30
    until python -c "
import psycopg
import os, sys
try:
    psycopg.connect(
        host=os.environ.get('POSTGRES_HOST', 'postgres'),
        port=os.environ.get('POSTGRES_PORT', '5432'),
        dbname=os.environ.get('POSTGRES_DB', 'safralog'),
        user=os.environ.get('POSTGRES_USER', 'safralog'),
        password=os.environ.get('POSTGRES_PASSWORD', ''),
    )
    print('PostgreSQL disponível!')
except Exception as e:
    sys.exit(1)
" 2>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            echo "❌ PostgreSQL não disponível. Abortando."
            exit 1
        fi
        echo "   Tentando novamente em 2s... ($retries tentativas restantes)"
        sleep 2
    done
}

# Aguarda Redis ficar disponível
wait_for_redis() {
    echo "⏳ Aguardando Redis..."
    local retries=15
    until python -c "
import redis, os, sys
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'))
    r.ping()
    print('Redis disponível!')
except Exception:
    sys.exit(1)
" 2>/dev/null; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            echo "⚠️  Redis não disponível. Continuando sem cache..."
            break
        fi
        sleep 1
    done
}

case "$1" in
    gunicorn)
        wait_for_postgres
        wait_for_redis

        echo "🔄 Rodando migrations..."
        python manage.py migrate --noinput

        echo "📦 Coletando arquivos estáticos..."
        python manage.py collectstatic --noinput --clear

        echo "🚀 Iniciando Gunicorn..."
        exec gunicorn config.wsgi:application \
            --config docker/django/gunicorn.conf.py
        ;;

    celery-worker)
        wait_for_postgres
        wait_for_redis
        echo "🔄 Iniciando Celery Worker..."
        exec celery -A config.celery worker \
            --loglevel="${LOG_LEVEL:-info}" \
            --concurrency=4 \
            --queues=default,high_priority,low_priority
        ;;

    celery-beat)
        wait_for_postgres
        wait_for_redis
        echo "⏰ Iniciando Celery Beat..."
        exec celery -A config.celery beat \
            --loglevel="${LOG_LEVEL:-info}" \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;

    flower)
        wait_for_redis
        echo "🌸 Iniciando Flower..."
        exec celery -A config.celery flower \
            --port="${FLOWER_PORT:-5555}" \
            --basic-auth="${FLOWER_USER:-admin}:${FLOWER_PASSWORD:-admin123}"
        ;;

    dev)
        wait_for_postgres
        wait_for_redis
        echo "🔄 Rodando migrations..."
        python manage.py migrate --noinput
        echo "🛠️  Iniciando servidor de desenvolvimento..."
        exec python manage.py runserver 0.0.0.0:8000
        ;;

    *)
        exec "$@"
        ;;
esac
