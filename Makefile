# =============================================================================
# SafraLog — Makefile
# =============================================================================
.DEFAULT_GOAL := help

.PHONY: help
.PHONY: build up down restart restart-all logs logs-all ps
.PHONY: shell shell-plain shell-db
.PHONY: migrate makemigrations makemigrations-app showmigrations
.PHONY: superuser check check-deploy
.PHONY: css css-watch assets static static-clear
.PHONY: celery beat flower
.PHONY: test test-coverage test-fast test-app
.PHONY: lint lint-fix format typecheck
.PHONY: backup seed reset-seed reset-db
.PHONY: prod-build prod-up prod-down prod-restart prod-deploy prod-logs
.PHONY: prod-shell prod-shell-db prod-ps
.PHONY: prod-migrate prod-static prod-check

DC      = docker compose -f infrastructure/docker-compose.yml
DC_DEV  = $(DC) -f infrastructure/docker-compose.dev.yml
DC_PROD = $(DC) -f infrastructure/docker-compose.prod.yml
DJANGO  = $(DC_DEV) exec django

PG_USER = safralog
PG_DB   = safralog

# Variável de settings para testes — sobrepõe o DJANGO_SETTINGS_MODULE do container
TEST_SETTINGS = DJANGO_SETTINGS_MODULE=config.settings.testing

# =============================================================================
# HELP
# =============================================================================
help: ## Mostra este menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-26s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# DOCKER — DESENVOLVIMENTO
# =============================================================================
build: ## Build todos os containers (sem cache)
	$(DC_DEV) build --no-cache

up: ## Sobe containers em modo desenvolvimento
	$(DC_DEV) up -d

down: ## Para todos os containers
	$(DC_DEV) down

restart: ## Reinicia o container Django sem rebuild
	$(DC_DEV) restart django

restart-all: down up ## Para e sobe todos os containers

logs: ## Logs do Django em tempo real
	$(DC_DEV) logs -f django

logs-all: ## Logs de todos os containers em tempo real
	$(DC_DEV) logs -f

ps: ## Lista containers e status
	$(DC_DEV) ps

# =============================================================================
# DJANGO — SHELL
# =============================================================================
shell: ## Django shell_plus com SQL (requer django-extensions)
	$(DJANGO) python manage.py shell_plus --print-sql

shell-plain: ## Django shell padrão
	$(DJANGO) python manage.py shell

shell-db: ## psql direto no container postgres
	$(DC_DEV) exec postgres psql -U $(PG_USER) -d $(PG_DB)

# =============================================================================
# DJANGO — MIGRATIONS
# =============================================================================
migrate: ## Aplica todas as migrations pendentes
	$(DJANGO) python manage.py migrate

makemigrations: ## Cria migrations para todos os apps
	$(DJANGO) python manage.py makemigrations

makemigrations-app: ## Cria migration para app específico: make makemigrations-app APP=finance
	$(DJANGO) python manage.py makemigrations $(APP)

showmigrations: ## Lista migrations e status de cada uma
	$(DJANGO) python manage.py showmigrations

# =============================================================================
# DJANGO — UTILITÁRIOS
# =============================================================================
superuser: ## Cria superusuário interativo
	$(DJANGO) python manage.py createsuperuser

check: ## Verifica configuração Django — uso diário (0 issues esperado)
	$(DJANGO) python manage.py check

check-deploy: ## Checklist completo de segurança — usar antes do deploy
	$(DJANGO) python manage.py check --deploy

# =============================================================================
# ASSETS — CSS / JS / STATIC
# =============================================================================
# npm roda no HOST (não no container) — Dockerfile multi-stage remove Node
# do runtime para manter a imagem leve.

css: ## Compila Tailwind CSS para produção (minificado)
	npm run build

css-watch: ## Compila Tailwind CSS em modo watch (desenvolvimento)
	npm run dev

static: ## Coleta arquivos estáticos no container (desenvolvimento)
	$(DJANGO) python manage.py collectstatic --noinput

static-clear: ## Coleta arquivos estáticos limpando destino antes (desenvolvimento)
	$(DJANGO) python manage.py collectstatic --noinput --clear

assets: css static ## Compila CSS + coleta estáticos (use após adicionar assets)

# =============================================================================
# CELERY
# =============================================================================
celery: ## Sobe worker Celery
	$(DC_DEV) up -d celery-worker

beat: ## Sobe Celery Beat (agendador de tarefas)
	$(DC_DEV) up -d celery-beat

flower: ## Sobe Flower — monitoramento Celery (http://localhost:5555)
	$(DC_DEV) up -d flower

# =============================================================================
# TESTES
# Usa TEST_SETTINGS para sobrepor o DJANGO_SETTINGS_MODULE do container,
# garantindo que debug_toolbar não carregue durante os testes.
# =============================================================================
test: ## Roda todos os testes com pytest
	$(DJANGO) bash -c '$(TEST_SETTINGS) python -m pytest tests/ apps/ -v --tb=short'

test-coverage: ## Roda testes com cobertura e gera relatório HTML
	$(DC_DEV) exec django bash -c \
	'$(TEST_SETTINGS) python -m pytest tests/ apps/ \
	  --cov=apps \
	  --cov-report=term-missing \
	  --cov-report=html:/tmp/htmlcov \
	  -q'

test-fast: ## Testes rápidos — para na primeira falha
	$(DJANGO) bash -c '$(TEST_SETTINGS) python -m pytest tests/ apps/ -x --tb=short -q'

test-app: ## Testes de um app específico: make test-app APP=logistics
	$(DJANGO) bash -c '$(TEST_SETTINGS) python -m pytest apps/$(APP)/ -v --tb=short'

# =============================================================================
# QUALIDADE DE CÓDIGO
# =============================================================================
lint: ## Linter ruff — mostra problemas sem corrigir
	$(DJANGO) ruff check apps/ config/ tests/

lint-fix: ## Linter + corrige automaticamente o que for possível
	$(DJANGO) ruff check apps/ config/ tests/ --fix

format: ## Formata código com ruff
	$(DJANGO) ruff format apps/ config/ tests/

typecheck: ## Checagem de tipos com mypy
	$(DJANGO) mypy apps/ config/

# =============================================================================
# BANCO DE DADOS
# =============================================================================
backup: ## Faz backup do banco de dados
	@bash scripts/backup_db.sh

seed: ## Popula dados de desenvolvimento (idempotente)
	$(DJANGO) bash -c 'PYTHONPATH=/app python /app/scripts/seed_dev_data.py'

reset-seed: ## Limpa dados de seed e repopula (mantém schema)
	$(DC_DEV) exec postgres psql -U $(PG_USER) -d $(PG_DB) -c "\
		DELETE FROM operations_waybill; \
		DELETE FROM logistics_fueling; \
		DELETE FROM logistics_driver; \
		DELETE FROM logistics_vehicle; \
		DELETE FROM operations_field; \
		DELETE FROM operations_harvest; \
		DELETE FROM finance_financialaccount; \
		DELETE FROM accounts_user WHERE email IN ('admin@safralog.dev','gerente@safralog.dev','operador@safralog.dev'); \
		DELETE FROM tenants_tenant WHERE slug = 'fazenda-demo'; \
	"
	$(MAKE) seed

reset-db: ## ⚠️  DESTRÓI e recria o banco inteiro (apenas dev)
	@echo "⚠️  Isso vai apagar TODOS os dados. Ctrl+C para cancelar."
	@sleep 3
	$(DC_DEV) exec postgres psql -U $(PG_USER) -c "DROP DATABASE IF EXISTS $(PG_DB);"
	$(DC_DEV) exec postgres psql -U $(PG_USER) -c "CREATE DATABASE $(PG_DB) OWNER $(PG_USER);"
	$(MAKE) migrate
	$(MAKE) seed

# =============================================================================
# PRODUÇÃO — COMANDOS INDIVIDUAIS
# =============================================================================
prod-build: ## Build imagens de produção
	$(DC_PROD) build

prod-up: ## Sobe ambiente de produção
	$(DC_PROD) up -d

prod-down: ## Para ambiente de produção
	$(DC_PROD) down

prod-restart: ## Reinicia container Django em produção sem rebuild
	$(DC_PROD) restart django

prod-ps: ## Lista containers de produção e status
	$(DC_PROD) ps

prod-logs: ## Logs de produção em tempo real (todos os containers)
	$(DC_PROD) logs -f

prod-shell: ## Django shell em produção (usar com cautela)
	$(DC_PROD) exec django python manage.py shell

prod-shell-db: ## psql direto no postgres de produção (usar com cautela)
	$(DC_PROD) exec postgres psql -U $(PG_USER) -d $(PG_DB)

prod-migrate: ## Aplica migrations em produção
	$(DC_PROD) exec django python manage.py migrate --noinput

prod-static: ## Coleta estáticos em produção (com --clear para evitar arquivos órfãos)
	$(DC_PROD) exec django python manage.py collectstatic --noinput --clear

prod-check: ## Checklist de segurança Django em produção
	$(DC_PROD) exec django python manage.py check --deploy

# =============================================================================
# PRODUÇÃO — DEPLOY COMPLETO
#
# Ordem: build → up → migrate → collectstatic
#
# --clear no collectstatic é obrigatório: evita FileNotFoundError no WhiteNoise
# quando arquivos órfãos de deploys anteriores permanecem em static_collected.
# Isso ocorre porque o CompressedManifestStaticFilesStorage tenta comprimir
# todos os arquivos referenciados no manifesto, incluindo os removidos.
# =============================================================================
prod-deploy: ## Deploy completo: build → up → migrate
	@echo "🚀 [1/3] Buildando imagens..."
	$(DC_PROD) build
	@echo "🚀 [2/3] Subindo containers..."
	$(DC_PROD) up -d
	@echo "🚀 [3/3] Aplicando migrations..."
	$(DC_PROD) exec django python manage.py migrate --noinput
	@echo "✅ Deploy concluído."
