#!/usr/bin/env bash
# =============================================================================
# SafraLog — scripts/deploy_hostinger.sh
# Deploy no VPS Hostinger via Docker Compose
#
# Uso:
#   chmod +x scripts/deploy_hostinger.sh
#   ./scripts/deploy_hostinger.sh
#
# Pré-requisitos no VPS:
#   - Docker + Docker Compose instalados
#   - .env.production preenchido na raiz do projeto
#   - npm instalado (para compilar CSS)
# =============================================================================
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_BASE="$PROJECT_DIR/infrastructure/docker-compose.yml"
COMPOSE_PROD="$PROJECT_DIR/infrastructure/docker-compose.prod.yml"

cd "$PROJECT_DIR"

echo "========================================="
echo "  SafraLog — Deploy Produção (Hostinger)"
echo "========================================="

# 1. Verificar .env.production
if [[ ! -f .env.production ]]; then
  echo "ERRO: .env.production não encontrado!"
  echo "Copie .env.production.example, preencha e tente novamente."
  exit 1
fi

if grep -q '\[PREENCHER\]' .env.production; then
  echo "ERRO: .env.production ainda contém campos [PREENCHER] não preenchidos!"
  grep '\[PREENCHER\]' .env.production
  exit 1
fi

echo "✓ .env.production validado"

# 2. Compilar CSS (TailwindCSS)
echo ""
echo "→ Compilando CSS (TailwindCSS)..."
if command -v npm &> /dev/null; then
  npm ci --silent
  npm run build 2>&1 | tail -5
  echo "✓ CSS compilado"
else
  echo "AVISO: npm não encontrado — pulando compilação de CSS"
  echo "       Execute 'npm run build' manualmente antes do deploy"
fi

# 3. Build das imagens Docker
echo ""
echo "→ Fazendo build das imagens Docker..."
docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  build --pull

echo "✓ Imagens construídas"

# 4. Subir os serviços
echo ""
echo "→ Subindo serviços..."
docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  up -d

echo "✓ Serviços iniciados"

# 5. Aguardar banco de dados
echo ""
echo "→ Aguardando banco de dados ficar pronto..."
for i in $(seq 1 30); do
  if docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
      exec -T postgres pg_isready -U safralog_user -d safralog &>/dev/null; then
    echo "✓ Banco pronto"
    break
  fi
  echo "   Aguardando... ($i/30)"
  sleep 2
done

# 6. Migrations
echo ""
echo "→ Aplicando migrations..."
docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  exec -T django python manage.py migrate --noinput

echo "✓ Migrations aplicadas"

# 7. Collectstatic
echo ""
echo "→ Coletando arquivos estáticos..."
docker compose \
  -f "$COMPOSE_BASE" \
  -f "$COMPOSE_PROD" \
  exec -T django python manage.py collectstatic --noinput --clear

echo "✓ Estáticos coletados"

# 8. Verificar saúde
echo ""
echo "→ Verificando health check..."
sleep 3
if docker compose -f "$COMPOSE_BASE" -f "$COMPOSE_PROD" \
    exec -T django python manage.py check --deploy 2>&1 | grep -q "0 issues"; then
  echo "✓ Sistema saudável"
else
  echo "AVISO: Verificar 'python manage.py check --deploy' manualmente"
fi

echo ""
echo "========================================="
echo "  Deploy concluído!"
echo ""
echo "  Próximos passos:"
echo "  1. Criar superusuário (primeira vez):"
echo "     docker compose exec django python manage.py createsuperuser"
echo ""
echo "  2. Criar o tenant inicial (primeira vez):"
echo "     docker compose exec django python manage.py shell -c \\"
echo "       \"from apps.tenants.models import Tenant; Tenant.objects.create(name='Grupo de Produtores', slug='grupo', status='active')\""
echo ""
echo "  3. Configurar SSL com Certbot:"
echo "     docker run --rm -v letsencrypt:/etc/letsencrypt -v certbot_webroot:/var/www/certbot \\"
echo "       certbot/certbot certonly --webroot -w /var/www/certbot -d SEU_DOMINIO"
echo "========================================="
