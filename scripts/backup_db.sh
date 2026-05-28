#!/usr/bin/env bash
# ============================================================
# SafraLog — Backup do PostgreSQL
# Uso: ./scripts/backup_db.sh [ambiente]
# Exemplos:
#   ./scripts/backup_db.sh          → backup do dev local
#   ./scripts/backup_db.sh prod     → backup do prod (via Docker)
# ============================================================
set -euo pipefail

# ── Configuração ─────────────────────────────────────────────
ENV="${1:-dev}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="./backups"
BACKUP_FILE="${BACKUP_DIR}/safralog_${ENV}_${TIMESTAMP}.sql.gz"

# Carrega .env se existir
if [ -f ".env" ]; then
  source <(grep -v '^#' .env | grep '=' | sed 's/^/export /')
fi

DB_NAME="${POSTGRES_DB:-safralog}"
DB_USER="${POSTGRES_USER:-safralog}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

# ── Criação do diretório de backups ───────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Backup ───────────────────────────────────────────────────
echo "📦 Iniciando backup: $BACKUP_FILE"
echo "   Banco: $DB_NAME | Host: $DB_HOST | Porta: $DB_PORT"
echo ""

if [ "$ENV" = "prod" ]; then
  # Via Docker Compose em produção
  docker compose -f infrastructure/docker-compose.yml \
    -f infrastructure/docker-compose.prod.yml \
    exec -T postgres \
    pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists \
    | gzip > "$BACKUP_FILE"
else
  # Direto (dev local)
  PGPASSWORD="${POSTGRES_PASSWORD:-safralog}" \
    pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --clean --if-exists \
    | gzip > "$BACKUP_FILE"
fi

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "✅ Backup concluído: $BACKUP_FILE ($SIZE)"
echo ""

# ── Limpeza: mantém apenas os últimos 30 backups ──────────────
KEEP=30
TOTAL=$(ls -1 "${BACKUP_DIR}/safralog_${ENV}_"*.sql.gz 2>/dev/null | wc -l)

if [ "$TOTAL" -gt "$KEEP" ]; then
  REMOVE=$((TOTAL - KEEP))
  echo "🗑️  Removendo $REMOVE backup(s) antigo(s)..."
  ls -1t "${BACKUP_DIR}/safralog_${ENV}_"*.sql.gz | tail -n "$REMOVE" | xargs rm -f
  echo "   Mantendo os últimos $KEEP backups."
fi

echo ""
echo "📋 Backups disponíveis:"
ls -lh "${BACKUP_DIR}/safralog_${ENV}_"*.sql.gz 2>/dev/null || echo "   (nenhum)"
