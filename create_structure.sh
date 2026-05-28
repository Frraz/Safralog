#!/usr/bin/env bash
# =============================================================================
# SafraLog — create_structure.sh
# Cria toda a estrutura de diretórios e arquivos do projeto.
# Executar na raiz do repositório (pasta SafraLog/).
# =============================================================================
set -euo pipefail

echo "🌾 SafraLog — Criando estrutura do projeto..."

# =============================================================================
# DIRETÓRIOS PRINCIPAIS
# =============================================================================
dirs=(
  # Config Django
  "config/settings"

  # Apps
  "apps/core/utils"
  "apps/core/templatetags"
  "apps/core/management/commands"
  "apps/accounts/tests"
  "apps/tenants"
  "apps/operations/models"
  "apps/operations/views"
  "apps/operations/services"
  "apps/operations/tests"
  "apps/operations/templatetags"
  "apps/logistics/models"
  "apps/logistics/views"
  "apps/logistics/services"
  "apps/logistics/tests"
  "apps/finance/models"
  "apps/finance/views"
  "apps/finance/services"
  "apps/finance/tests"
  "apps/attachments/tests"
  "apps/reports/views"
  "apps/reports/services"
  "apps/dashboard/tests"
  "apps/notifications"

  # Templates globais
  "templates/partials"
  "templates/components"
  "templates/accounts"
  "templates/dashboard"
  "templates/operations"
  "templates/logistics"
  "templates/finance"
  "templates/attachments"
  "templates/reports/pdf"

  # Static
  "static/css"
  "static/js"
  "static/img"
  "static/fonts"

  # Media
  "media"

  # Requirements
  "requirements"

  # Docker
  "docker/django"
  "docker/nginx"
  "docker/postgres"

  # Infrastructure
  "infrastructure"

  # Scripts
  "scripts"

  # Docs
  "docs"

  # Tests globais
  "tests/factories"
  "tests/integration"
  "tests/unit"
)

for d in "${dirs[@]}"; do
  mkdir -p "$d"
done

# =============================================================================
# ARQUIVOS
# =============================================================================
files=(
  # Root
  ".env.example"
  ".env"
  ".gitignore"
  ".dockerignore"
  "Makefile"
  "pyproject.toml"
  "README.md"
  "manage.py"
  "package.json"
  "tailwind.config.js"
  "postcss.config.js"

  # Config
  "config/__init__.py"
  "config/asgi.py"
  "config/wsgi.py"
  "config/celery.py"
  "config/urls.py"
  "config/settings/__init__.py"
  "config/settings/base.py"
  "config/settings/development.py"
  "config/settings/production.py"
  "config/settings/testing.py"

  # App: core
  "apps/__init__.py"
  "apps/core/__init__.py"
  "apps/core/apps.py"
  "apps/core/models.py"
  "apps/core/admin.py"
  "apps/core/middleware.py"
  "apps/core/context_processors.py"
  "apps/core/exceptions.py"
  "apps/core/constants.py"
  "apps/core/utils/__init__.py"
  "apps/core/utils/formatters.py"
  "apps/core/utils/validators.py"
  "apps/core/utils/decorators.py"
  "apps/core/utils/pagination.py"
  "apps/core/templatetags/__init__.py"
  "apps/core/templatetags/core_tags.py"
  "apps/core/management/__init__.py"
  "apps/core/management/commands/__init__.py"
  "apps/core/management/commands/create_tenant.py"

  # App: accounts
  "apps/accounts/__init__.py"
  "apps/accounts/apps.py"
  "apps/accounts/models.py"
  "apps/accounts/admin.py"
  "apps/accounts/forms.py"
  "apps/accounts/views.py"
  "apps/accounts/urls.py"
  "apps/accounts/services.py"
  "apps/accounts/selectors.py"
  "apps/accounts/backends.py"
  "apps/accounts/tests/__init__.py"
  "apps/accounts/tests/test_models.py"
  "apps/accounts/tests/test_views.py"

  # App: tenants
  "apps/tenants/__init__.py"
  "apps/tenants/apps.py"
  "apps/tenants/models.py"
  "apps/tenants/admin.py"
  "apps/tenants/middleware.py"
  "apps/tenants/services.py"
  "apps/tenants/selectors.py"

  # App: operations
  "apps/operations/__init__.py"
  "apps/operations/apps.py"
  "apps/operations/admin.py"
  "apps/operations/forms.py"
  "apps/operations/urls.py"
  "apps/operations/selectors.py"
  "apps/operations/signals.py"
  "apps/operations/tasks.py"
  "apps/operations/models/__init__.py"
  "apps/operations/models/harvest.py"
  "apps/operations/models/field.py"
  "apps/operations/models/waybill.py"
  "apps/operations/views/__init__.py"
  "apps/operations/views/harvest.py"
  "apps/operations/views/field.py"
  "apps/operations/views/waybill.py"
  "apps/operations/services/__init__.py"
  "apps/operations/services/waybill_service.py"
  "apps/operations/services/field_service.py"
  "apps/operations/templatetags/__init__.py"
  "apps/operations/templatetags/operations_tags.py"
  "apps/operations/tests/__init__.py"
  "apps/operations/tests/test_waybill.py"

  # App: logistics
  "apps/logistics/__init__.py"
  "apps/logistics/apps.py"
  "apps/logistics/admin.py"
  "apps/logistics/forms.py"
  "apps/logistics/urls.py"
  "apps/logistics/selectors.py"
  "apps/logistics/signals.py"
  "apps/logistics/tasks.py"
  "apps/logistics/models/__init__.py"
  "apps/logistics/models/driver.py"
  "apps/logistics/models/vehicle.py"
  "apps/logistics/models/fueling.py"
  "apps/logistics/views/__init__.py"
  "apps/logistics/views/driver.py"
  "apps/logistics/views/vehicle.py"
  "apps/logistics/views/fueling.py"
  "apps/logistics/services/__init__.py"
  "apps/logistics/services/fueling_service.py"
  "apps/logistics/tests/__init__.py"

  # App: finance
  "apps/finance/__init__.py"
  "apps/finance/apps.py"
  "apps/finance/admin.py"
  "apps/finance/forms.py"
  "apps/finance/urls.py"
  "apps/finance/selectors.py"
  "apps/finance/signals.py"
  "apps/finance/tasks.py"
  "apps/finance/models/__init__.py"
  "apps/finance/models/account.py"
  "apps/finance/models/ledger.py"
  "apps/finance/models/advance.py"
  "apps/finance/models/settlement.py"
  "apps/finance/views/__init__.py"
  "apps/finance/views/ledger.py"
  "apps/finance/views/advance.py"
  "apps/finance/views/settlement.py"
  "apps/finance/services/__init__.py"
  "apps/finance/services/ledger_service.py"
  "apps/finance/services/settlement_service.py"
  "apps/finance/services/advance_service.py"
  "apps/finance/tests/__init__.py"
  "apps/finance/tests/test_ledger.py"

  # App: attachments
  "apps/attachments/__init__.py"
  "apps/attachments/apps.py"
  "apps/attachments/models.py"
  "apps/attachments/admin.py"
  "apps/attachments/views.py"
  "apps/attachments/urls.py"
  "apps/attachments/services.py"
  "apps/attachments/utils.py"
  "apps/attachments/tests/__init__.py"

  # App: reports
  "apps/reports/__init__.py"
  "apps/reports/apps.py"
  "apps/reports/urls.py"
  "apps/reports/views/__init__.py"
  "apps/reports/views/waybill_pdf.py"
  "apps/reports/views/settlement_pdf.py"
  "apps/reports/services/__init__.py"
  "apps/reports/services/pdf_service.py"

  # App: dashboard
  "apps/dashboard/__init__.py"
  "apps/dashboard/apps.py"
  "apps/dashboard/views.py"
  "apps/dashboard/urls.py"
  "apps/dashboard/selectors.py"
  "apps/dashboard/tests/__init__.py"

  # App: notifications
  "apps/notifications/__init__.py"
  "apps/notifications/apps.py"
  "apps/notifications/models.py"
  "apps/notifications/services.py"
  "apps/notifications/tasks.py"

  # Templates
  "templates/base.html"
  "templates/partials/sidebar.html"
  "templates/partials/navbar.html"
  "templates/partials/messages.html"
  "templates/partials/pagination.html"
  "templates/partials/breadcrumb.html"
  "templates/components/modal.html"
  "templates/components/upload_zone.html"
  "templates/components/empty_state.html"
  "templates/components/stat_card.html"
  "templates/components/table_actions.html"
  "templates/components/confirm_dialog.html"
  "templates/accounts/login.html"
  "templates/accounts/profile.html"
  "templates/dashboard/index.html"
  "templates/operations/waybill/list.html"
  "templates/operations/waybill/detail.html"
  "templates/operations/waybill/form.html"
  "templates/operations/waybill/_row.html"
  "templates/operations/field/list.html"
  "templates/operations/field/form.html"
  "templates/logistics/driver/list.html"
  "templates/logistics/driver/form.html"
  "templates/logistics/vehicle/list.html"
  "templates/logistics/fueling/list.html"
  "templates/logistics/fueling/form.html"
  "templates/finance/ledger/list.html"
  "templates/finance/advance/list.html"
  "templates/finance/advance/form.html"
  "templates/finance/settlement/list.html"
  "templates/finance/settlement/detail.html"
  "templates/attachments/upload_widget.html"
  "templates/reports/pdf/waybill.html"
  "templates/reports/pdf/settlement.html"
  "templates/reports/pdf/base_pdf.html"

  # Static
  "static/css/main.css"
  "static/js/main.js"
  "static/js/htmx-config.js"
  "static/js/upload.js"
  "static/img/logo.svg"

  # Requirements
  "requirements/base.txt"
  "requirements/development.txt"
  "requirements/production.txt"

  # Docker
  "docker/django/Dockerfile"
  "docker/django/entrypoint.sh"
  "docker/django/gunicorn.conf.py"
  "docker/nginx/Dockerfile"
  "docker/nginx/nginx.conf"
  "docker/nginx/default.conf"
  "docker/postgres/init.sql"

  # Infrastructure
  "infrastructure/docker-compose.yml"
  "infrastructure/docker-compose.dev.yml"
  "infrastructure/docker-compose.prod.yml"

  # Scripts
  "scripts/backup_db.sh"
  "scripts/restore_db.sh"
  "scripts/create_superuser.py"
  "scripts/seed_dev_data.py"

  # Docs
  "docs/architecture.md"
  "docs/development.md"
  "docs/deployment.md"
  "docs/financial_model.md"

  # Tests globais
  "tests/__init__.py"
  "tests/conftest.py"
  "tests/factories/__init__.py"
  "tests/factories/accounts.py"
  "tests/factories/operations.py"
  "tests/factories/finance.py"
)

for f in "${files[@]}"; do
  touch "$f"
done

echo ""
echo "✅ Estrutura criada com sucesso!"
echo ""
echo "Próximos passos:"
echo "  1. cp .env.example .env  — configure suas variáveis"
echo "  2. make build            — builda containers"
echo "  3. make up               — sobe containers"
echo "  4. make migrate          — roda migrations"
echo "  5. make superuser        — cria superusuário"
echo ""
