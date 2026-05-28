#!/usr/bin/env bash
# =============================================================================
# SafraLog — scripts/deploy_vps.sh
# Deploy no VPS Hostinger (147.93.15.214)
# Segue o padrão do servidor: nginx HOST, containers sem 80/443
#
# Uso no VPS:
#   chmod +x /var/www/docker-instances/SafraLog/scripts/deploy_vps.sh
#   ./scripts/deploy_vps.sh
#
# Pré-requisitos no VPS:
#   - Docker + Docker Compose instalados
#   - .env.production preenchido (SECRET_KEY, DB password, email)
#   - npm instalado (para compilar TailwindCSS + bundles JS)
# =============================================================================
set -euo pipefail

DEPLOY_DIR="/var/www/docker-instances/SafraLog"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_BASE="$PROJECT_DIR/infrastructure/docker-compose.yml"
COMPOSE_PROD="$PROJECT_DIR/infrastructure/docker-compose.prod.yml"

echo "╔══════════════════════════════════════════╗"
echo "║  SafraLog — Deploy VPS Hostinger         ║"
echo "║  safralog.ferzion.com.br → :8120         ║"
echo "╚══════════════════════════════════════════╝"

cd "$PROJECT_DIR"

# 1. Verificar .env.production
if [[ ! -f .env.production ]]; then
  echo "ERRO: .env.production não encontrado!"
  exit 1
fi
if grep -q '\[PREENCHER\]' .env.production; then
  echo "ERRO: .env.production ainda contém campos [PREENCHER]:"
  grep '\[PREENCHER\]' .env.production
  exit 1
fi
echo "✓ .env.production OK"

# 2. Verificar conflito de porta (segurança — não pode usar 80/443)
if docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" config 2>/dev/null | grep -E '"80:80"|"443:443"'; then
  echo "ERRO CRÍTICO: docker-compose expõe porta 80 ou 443!"
  echo "Isso quebraria todos os outros sistemas no servidor."
  exit 1
fi
echo "✓ Sem conflito de portas 80/443"

# 3. Criar diretórios necessários para bind mounts
echo ""
echo "→ Criando diretórios de dados..."
mkdir -p "$DEPLOY_DIR/media"
mkdir -p "$DEPLOY_DIR/static_collected"
echo "✓ Diretórios criados"

# 4. Compilar CSS e bundles JS
echo ""
echo "→ Compilando CSS (TailwindCSS) e copiando bundles..."
if command -v npm &>/dev/null; then
  npm ci --silent
  npm run build 2>&1 | tail -3
  echo "✓ CSS compilado e vendors copiados"
else
  echo "AVISO: npm não encontrado — instale com: curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - && apt-get install -y nodejs"
fi

# 5. Build e subida dos containers
echo ""
echo "→ Build e inicialização dos containers..."
docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  up -d --build

echo "✓ Containers iniciados"

# 6. Aguardar banco de dados
echo ""
echo "→ Aguardando banco de dados..."
for i in $(seq 1 30); do
  if docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
      exec -T postgres pg_isready -U safralog_user -d safralog &>/dev/null; then
    echo "✓ Banco pronto"
    break
  fi
  printf "   Aguardando... $i/30\r"
  sleep 2
done

# 7. Migrations
echo ""
echo "→ Aplicando migrations..."
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
  exec -T django python manage.py migrate --noinput
echo "✓ Migrations aplicadas"

# 8. Collectstatic
echo ""
echo "→ Coletando arquivos estáticos..."
docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
  exec -T django python manage.py collectstatic --noinput --clear
echo "✓ Estáticos coletados em $DEPLOY_DIR/static_collected/"

# 9. Verificar nginx do host
echo ""
echo "→ Configurando nginx do host..."
NGINX_CONF="/etc/nginx/sites-available/safralog.ferzion.com.br"
if [[ ! -f "$NGINX_CONF" ]]; then
  echo ""
  echo "══════════════════════════════════════════════════════"
  echo "  PRÓXIMO PASSO MANUAL: Configurar nginx do host"
  echo "══════════════════════════════════════════════════════"
  echo ""
  echo "1. Copiar config do nginx:"
  echo "   sudo cp $PROJECT_DIR/docker/nginx/safralog.ferzion.com.br.conf \\"
  echo "           /etc/nginx/sites-available/safralog.ferzion.com.br"
  echo ""
  echo "2. Ativar:"
  echo "   sudo ln -s /etc/nginx/sites-available/safralog.ferzion.com.br \\"
  echo "              /etc/nginx/sites-enabled/safralog.ferzion.com.br"
  echo ""
  echo "3. Obter certificado SSL:"
  echo "   sudo certbot certonly --nginx -d safralog.ferzion.com.br"
  echo ""
  echo "4. Testar e recarregar:"
  echo "   sudo nginx -t && sudo systemctl reload nginx"
else
  sudo nginx -t && sudo systemctl reload nginx && echo "✓ Nginx recarregado"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Deploy concluído!                                       ║"
echo "║                                                          ║"
echo "║  Container: django → 127.0.0.1:8120                     ║"
echo "║  URL:       https://safralog.ferzion.com.br              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Primeiro acesso (somente na primeira vez):"
echo "  # Criar superusuário:"
echo "  docker compose exec django python manage.py createsuperuser"
echo ""
echo "  # Criar tenant inicial:"
echo "  docker compose exec django python manage.py shell -c \\"
echo "    \"from apps.tenants.models import Tenant; Tenant.objects.create(name='Grupo de Produtores', slug='grupo', status='active')\""
