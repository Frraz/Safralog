#!/usr/bin/env bash
# =============================================================================
# SafraLog — scripts/deploy_vps.sh
# Deploy no VPS Hostinger (147.93.15.214)
# Segue o padrão do servidor: nginx HOST, containers sem 80/443
#
# Uso no VPS:
#   chmod +x /var/www/docker-instances/Safralog/scripts/deploy_vps.sh
#   ./scripts/deploy_vps.sh
#
# Pré-requisitos no VPS:
#   - Docker + Docker Compose instalados
#   - .env.production preenchido (SECRET_KEY, DB password, email)
#   - npm instalado (para compilar TailwindCSS + bundles JS)
# =============================================================================
set -euo pipefail

# =============================================================================
# Configuração
# =============================================================================
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="/var/www/docker-instances/SafraLog"
COMPOSE_BASE="$PROJECT_DIR/infrastructure/docker-compose.yml"
COMPOSE_PROD="$PROJECT_DIR/infrastructure/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.production"

# Atalho para todos os comandos docker compose (evita repetição e garante --env-file)
DC="docker compose --env-file $ENV_FILE -f $COMPOSE_BASE -f $COMPOSE_PROD"

# =============================================================================
# Helpers
# =============================================================================
ok()   { echo "  ✓ $*"; }
info() { echo ""; echo "→ $*..."; }
err()  { echo ""; echo "  ✗ ERRO: $*" >&2; exit 1; }

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║  SafraLog — Deploy VPS Hostinger         ║"
echo "║  safralog.ferzion.com.br → :8120         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

cd "$PROJECT_DIR"

# =============================================================================
# 1. Verificar .env.production
# =============================================================================
info "Verificando .env.production"

[[ -f "$ENV_FILE" ]] || err ".env.production não encontrado em $PROJECT_DIR"

if grep -q '\[PREENCHER\]' "$ENV_FILE"; then
  echo "  ✗ ERRO: .env.production ainda contém campos não preenchidos:" >&2
  grep '\[PREENCHER\]' "$ENV_FILE" >&2
  exit 1
fi

ok ".env.production OK"

# =============================================================================
# 2. Verificar que não há exposição de porta 80/443
# =============================================================================
info "Verificando conflito de portas críticas (80/443)"

if $DC config 2>/dev/null | grep -qE '"(80|443):'; then
  err "docker-compose expõe porta 80 ou 443 — isso quebraria os outros sistemas do servidor!"
fi

ok "Sem conflito de portas 80/443"

# =============================================================================
# 3. Criar diretórios necessários para bind mounts
# =============================================================================
info "Criando diretórios de dados"

mkdir -p "$DEPLOY_DIR/media"
mkdir -p "$DEPLOY_DIR/static_collected"

ok "Diretórios criados"

# =============================================================================
# 4. Compilar CSS e bundles JS (no host, antes do build Docker)
# =============================================================================
info "Compilando CSS (TailwindCSS) e copiando bundles JS"

if command -v npm &>/dev/null; then
  npm ci --silent
  npm run build 2>&1 | grep -v '^$' | tail -5
  ok "CSS compilado e vendors copiados"
else
  echo "  ! AVISO: npm não encontrado — CSS não será recompilado."
  echo "    Para instalar: curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && apt-get install -y nodejs"
fi

# =============================================================================
# 5. Build e subida dos containers
# =============================================================================
info "Build e inicialização dos containers"

$DC up -d --build

ok "Containers iniciados"

# =============================================================================
# 6. Aguardar o banco de dados estar pronto
# =============================================================================
info "Aguardando banco de dados"

# Lê o usuário do postgres direto do env file para não hardcodar
POSTGRES_USER_VAL=$(grep '^POSTGRES_USER=' "$ENV_FILE" | cut -d= -f2 | tr -d '"' | tr -d "'")
POSTGRES_DB_VAL=$(grep '^POSTGRES_DB=' "$ENV_FILE" | cut -d= -f2 | tr -d '"' | tr -d "'")

DB_READY=false
for i in $(seq 1 30); do
  if $DC exec -T postgres pg_isready -U "$POSTGRES_USER_VAL" -d "$POSTGRES_DB_VAL" &>/dev/null; then
    DB_READY=true
    break
  fi
  printf "    Aguardando postgres... tentativa %d/30\r" "$i"
  sleep 2
done

$DB_READY || err "Banco de dados não ficou pronto após 60 segundos. Verifique: $DC logs postgres"

ok "Banco pronto"

# =============================================================================
# 7. Migrations
# =============================================================================
info "Aplicando migrations"

$DC exec -T django python manage.py migrate --noinput

ok "Migrations aplicadas"

# =============================================================================
# 8. Collectstatic
# =============================================================================
info "Coletando arquivos estáticos"

$DC exec -T django python manage.py collectstatic --noinput

ok "Estáticos coletados em $DEPLOY_DIR/static_collected/"

# =============================================================================
# 9. Nginx do host
# =============================================================================
info "Verificando configuração do nginx"

NGINX_CONF="/etc/nginx/sites-available/safralog.ferzion.com.br"

if [[ ! -f "$NGINX_CONF" ]]; then
  echo ""
  echo "  ════════════════════════════════════════════════════════"
  echo "    PRÓXIMO PASSO MANUAL: Configurar nginx do host"
  echo "  ════════════════════════════════════════════════════════"
  echo ""
  echo "  1. Copiar config:"
  echo "     sudo cp $PROJECT_DIR/docker/nginx/safralog.ferzion.com.br.conf \\"
  echo "              /etc/nginx/sites-available/safralog.ferzion.com.br"
  echo ""
  echo "  2. Ativar o site:"
  echo "     sudo ln -s /etc/nginx/sites-available/safralog.ferzion.com.br \\"
  echo "                /etc/nginx/sites-enabled/safralog.ferzion.com.br"
  echo ""
  echo "  3. Obter certificado SSL:"
  echo "     sudo certbot certonly --nginx -d safralog.ferzion.com.br"
  echo ""
  echo "  4. Testar e recarregar:"
  echo "     sudo nginx -t && sudo systemctl reload nginx"
else
  if sudo nginx -t 2>/dev/null; then
    sudo systemctl reload nginx
    ok "Nginx recarregado"
  else
    echo "  ! AVISO: nginx -t falhou — verifique a config manualmente com: sudo nginx -t"
  fi
fi

# =============================================================================
# Resumo final
# =============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Deploy concluído com sucesso!                           ║"
echo "║                                                          ║"
echo "║  Container: safralog-django-1 → 127.0.0.1:8120          ║"
echo "║  URL:       https://safralog.ferzion.com.br              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Comandos úteis:"
echo ""
echo "  # Ver status dos containers:"
echo "  $DC ps"
echo ""
echo "  # Ver logs do Django em tempo real:"
echo "  $DC logs -f django"
echo ""
echo "  ── Apenas na primeira vez ──────────────────────────────"
echo ""
echo "  # Criar superusuário:"
echo "  $DC exec django python manage.py createsuperuser"
echo ""
echo "  # Criar tenant inicial:"
echo "  $DC exec django python manage.py shell -c \\"
echo "    \"from apps.tenants.models import Tenant; Tenant.objects.create(name='Grupo de Produtores', slug='grupo', status='active')\""
echo ""
