# SafraLog

> Sistema de logística e gestão financeira para operações agrícolas.  
> **Produção:** https://safralog.ferzion.com.br (VPS Hostinger — porta 8120)

SafraLog é um sistema para gerenciar operações de colheita, transporte de grãos e liquidação financeira de motoristas. Desenvolvido para funcionar em campo, com internet limitada, celular e ritmo intenso de safra.

**Problema resolvido:** gestores que recebem tudo via WhatsApp (imagens de romaneios, áudios de confirmação, comprovantes de abastecimento) precisam consolidar, calcular e gerar fechamentos em PDF de forma ágil. O sistema permite colar imagens diretamente do WhatsApp (Ctrl+V), calcular automaticamente o saldo e gerar o PDF de acerto pronto para impressão e pagamento.

---

## Sumário

- [Visão geral](#visão-geral)
- [Stack](#stack)
- [Funcionalidades](#funcionalidades)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Desenvolvimento](#desenvolvimento)
- [Comandos disponíveis](#comandos-disponíveis)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Arquitetura](#arquitetura)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Testes](#testes)
- [Deploy](#deploy)

---

## Visão geral

SafraLog centraliza o fluxo operacional e financeiro de uma safra:

```
Romaneio de viagem → Confirmação → Ledger financeiro → Fechamento com motorista
       ↓                                                         ↓
   Anexos / fotos                                          PDF de acerto
```

**Para quem:** Fazendas e operações agrícolas que precisam controlar tonelagem transportada, custo de combustível e acerto com motoristas de forma rastreável e auditável.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Django 5.1 + Python 3.12 |
| Banco | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Tarefas assíncronas | Celery 5 + Celery Beat |
| Frontend | HTMX 2 + Alpine.js 3 + TailwindCSS 3.4 |
| PDFs | WeasyPrint 63 |
| Auth | django-allauth 65 |
| Auditoria | django-simple-history 3.7 |
| Containerização | Docker + Docker Compose |
| Servidor web (prod) | Gunicorn + Nginx |
| Storage (prod) | AWS S3 via django-storages |
| Monitoramento Celery | Flower |
| Email dev | MailHog |
| Linter / Formatter | Ruff |
| Testes | pytest + factory-boy |

---

## Funcionalidades

### Operacional
- **Romaneios** — registro de cada viagem com motorista, veículo, talhão, pesagem (bruto/tara) e cultura
- **Safras** — organização por safra com área esperada e produtividade alvo
- **Talhões** — mapeamento de talhões com área e localização
- **Status tracking** — rascunho → confirmado → fechado (com auditoria completa)

### Logística
- **Motoristas** — cadastro com CNH, categoria, validade e conta financeira automática
- **Proprietários** — dono do caminhão (favorecido no pagamento), com dados bancários e chave PIX
- **Veículos** — frota com tipo, capacidade, motorista padrão e vínculo com proprietário
- **Abastecimentos** — preço duplo: valor do posto (registro) + valor descontado do motorista; extras no cupom (Arla, etc.)

### Operacional
- **Regiões** — preço padrão por tonelada por região de origem (Miguel Baiano, Rio Duro, etc.)
- **Talhões** — vinculados a regiões; ao selecionar o talhão no romaneio, o preço é preenchido automaticamente

### Financeiro
- **Ledger imutável** — toda movimentação gera entradas permanentes (crédito/débito)
- **Contas por motorista/proprietário** — saldo em tempo real via agregação do ledger
- **Adiantamentos** — registro de adiantamentos com débito automático na conta
- **Fechamentos** — acerto com snapshot imutável e PDF, fluxo: Rascunho → Aprovado → **Pago** (com comprovante)
- **Ajuste de valores** — qualquer valor do fechamento pode ser editado manualmente antes do pagamento (carga parcial paga como cheia, desconto negociado, etc.)
- **Comprovante de pagamento** — upload do PIX ou carta de quitação vinculado ao fechamento

### Plataforma
- **Multi-tenant** — isolamento completo de dados por fazenda/empresa
- **Auditoria total** — histórico de alterações com usuário, IP e timestamp (django-simple-history)
- **Soft delete** — nenhum dado importante é removido fisicamente
- **Uploads** — anexos em romaneios e motoristas (fotos, PDFs, documentos)
- **Notificações** — alertas em tempo real para eventos críticos
- **Dark mode** — interface adaptável com preferência salva no browser
- **Mobile-first** — funciona bem em celular e tablet para uso em campo

---

## Pré-requisitos

- **Docker** ≥ 24 e **Docker Compose** ≥ 2.20
- **Node.js** ≥ 18 e **npm** ≥ 9 (apenas no host, para compilar o CSS)
- **Git**

> O Node.js é necessário apenas para compilar o Tailwind CSS. O container Django não usa Node em runtime.

---

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/sua-org/safralog.git
cd safralog
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o `.env` com seus valores. Para desenvolvimento local, os valores padrão já funcionam.

### 3. Instale dependências Node (apenas no host)

```bash
npm install
```

### 4. Compile o CSS

```bash
npm run build
```

### 5. Suba os containers

```bash
make up
```

Aguarde todos os serviços ficarem saudáveis:

```bash
make ps
```

```
NAME                    STATUS
safralog-django-1       Up (healthy)
safralog-postgres-1     Up (healthy)
safralog-redis-1        Up (healthy)
safralog-celery-1       Up
safralog-beat-1         Up
safralog-flower-1       Up
safralog-mailhog-1      Up
```

### 6. Aplique as migrations

```bash
make migrate
```

### 7. Popule dados de desenvolvimento

```bash
make seed
```

Cria automaticamente:
- Tenant: **Fazenda Santa Fé Demo**
- Admin: `admin@safralog.dev` / `admin123`
- Gerente: `gerente@safralog.dev` / `gerente123`
- Operador: `operador@safralog.dev` / `op123`
- 6 motoristas com contas financeiras
- 4 veículos
- 5 talhões
- 60 romaneios de exemplo

### 8. Colete os arquivos estáticos

```bash
make static
```

### 9. Acesse

| Serviço | URL |
|---|---|
| Aplicação | http://localhost:8000 |
| Admin Django | http://localhost:8000/admin |
| Flower (Celery) | http://localhost:5555 |
| MailHog (email) | http://localhost:8025 |

---

## Configuração

### Variáveis de ambiente

Todas as variáveis estão documentadas em `.env.example`. As principais:

| Variável | Descrição | Padrão dev |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | Módulo de settings | `config.settings.development` |
| `DJANGO_SECRET_KEY` | Chave secreta Django | — (obrigatório) |
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql://safralog:...@postgres:5432/safralog` |
| `REDIS_URL` | URL Redis principal | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Broker Celery | `redis://redis:6379/1` |
| `STORAGE_BACKEND` | `local` ou `s3` | `local` |
| `AWS_STORAGE_BUCKET_NAME` | Bucket S3 (produção) | — |

### Módulos de settings

```
config/settings/
├── base.py          # Configurações compartilhadas
├── development.py   # Dev: Debug Toolbar, LocMemCache, SessionEngine=db, MailHog
├── production.py    # Prod: HTTPS, HSTS, S3, Sentry
└── testing.py       # Testes: banco separado, cache desativado
```

---

## Desenvolvimento

### Fluxo diário

```bash
# 1. Sobe os containers
make up

# 2. Em outro terminal — watch do CSS (recompila ao salvar templates)
make css-watch

# 3. Acompanha logs do Django
make logs
```

### Após alterar templates (novas classes Tailwind)

```bash
make css        # Recompila CSS
make static     # Coleta estáticos no container
```

### Após criar arquivos estáticos novos (JS, imagens)

```bash
make assets     # css + static em um comando
```

### Migrations

```bash
# Criar migration para um app
make makemigrations-app APP=finance

# Criar para todos
make makemigrations

# Aplicar
make migrate
```

### Reset completo do banco de dados

```bash
# Apaga apenas os dados de seed e repopula (mantém schema)
make reset-seed

# Apaga e recria o banco inteiro + migrate + seed
make reset-db
```

### Shell interativo

```bash
# Django shell com SQL impresso (requer django-extensions)
make shell

# Shell padrão
make shell-plain

# psql direto
make shell-db
```

---

## Comandos disponíveis

```
make help
```

| Comando | Descrição |
|---|---|
| `make up` | Sobe todos os containers |
| `make down` | Para todos os containers |
| `make restart` | Reinicia apenas o Django |
| `make logs` | Logs do Django em tempo real |
| `make logs-all` | Logs de todos os containers |
| `make ps` | Status dos containers |
| `make shell` | Django shell_plus com SQL |
| `make shell-db` | psql no container postgres |
| `make migrate` | Aplica migrations |
| `make makemigrations` | Cria migrations |
| `make seed` | Popula dados de dev (idempotente) |
| `make reset-seed` | Limpa dados e repopula |
| `make reset-db` | ⚠️ Destrói e recria banco |
| `make css` | Compila Tailwind CSS |
| `make css-watch` | Compila Tailwind em watch mode |
| `make static` | Coleta estáticos |
| `make assets` | CSS + static em sequência |
| `make test` | Roda todos os testes |
| `make test-app APP=x` | Testes de um app específico |
| `make test-coverage` | Testes com relatório de cobertura |
| `make lint` | Linter (ruff) |
| `make format` | Formata código (ruff) |
| `make lint-fix` | Lint + correção automática |
| `make check` | `manage.py check` — valida configuração |
| `make prod-deploy` | Build + migrate + collectstatic em prod |

---

## Estrutura do projeto

```
safralog/
├── apps/
│   ├── core/                   # BaseModel, mixins, middlewares, template tags
│   │   ├── middleware.py       # TenantMiddleware, TimezoneMiddleware, LastSeenMiddleware
│   │   ├── mixins.py           # TenantRequiredMixin, RoleRequiredMixin, HTMXMixin
│   │   └── templatetags/
│   │       └── core_tags.py    # sidebar_link, status badges, currency_br, kg_to_tons...
│   ├── accounts/               # User model, auth, perfil
│   ├── tenants/                # Tenant model, middleware
│   ├── operations/             # Harvest, Field, Waybill
│   │   ├── models/
│   │   ├── views/
│   │   │   ├── waybill.py
│   │   │   ├── harvest.py
│   │   │   └── field.py
│   │   └── forms/
│   ├── logistics/              # Driver, Vehicle, Fueling
│   │   ├── models/
│   │   └── views/
│   ├── finance/                # FinancialAccount, LedgerEntry, Settlement, Advance
│   │   ├── models/
│   │   ├── services/
│   │   │   ├── ledger_service.py
│   │   │   └── settlement_service.py
│   │   └── views/
│   ├── attachments/            # Attachment genérico
│   ├── notifications/          # Notification
│   ├── reports/                # PDFs via WeasyPrint
│   └── dashboard/              # Dashboard principal, selectors, quick search
│       ├── selectors.py        # Queries otimizadas do dashboard
│       └── views.py
│
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   ├── production.py
│   │   └── testing.py
│   ├── urls.py
│   └── celery.py
│
├── templates/
│   ├── base.html
│   ├── partials/               # sidebar, navbar, messages, pagination
│   ├── components/             # upload_zone
│   ├── accounts/               # login
│   ├── dashboard/
│   ├── operations/
│   │   └── waybill/            # list, _table, form, detail
│   ├── logistics/
│   │   └── driver/             # list, form, detail
│   ├── notifications/
│   └── reports/
│
├── static/
│   ├── css/
│   │   ├── main.css            # Entrada Tailwind (source)
│   │   └── dist/
│   │       └── main.css        # CSS compilado (gerado por npm run build)
│   ├── js/
│   │   ├── main.js             # Alpine.js e utilitários gerais
│   │   ├── upload.js           # Upload assíncrono de anexos
│   │   └── htmx-config.js      # CSRF header para HTMX
│   └── img/
│       └── logo.svg
│
├── scripts/
│   ├── seed_dev_data.py        # Seed idempotente de dados de dev
│   └── backup_db.sh
│
├── tests/
│   ├── conftest.py
│   ├── factories/
│   └── test_waybill.py
│
├── infrastructure/
│   ├── docker-compose.yml      # Base
│   ├── docker-compose.dev.yml  # Dev overrides (ports, volumes, debug)
│   └── docker-compose.prod.yml # Prod overrides (gunicorn, nginx)
│
├── docker/
│   ├── django/
│   │   ├── Dockerfile          # Multi-stage: Node (CSS) + Python runtime
│   │   ├── entrypoint.sh
│   │   └── gunicorn.conf.py
│   ├── nginx/
│   └── postgres/
│       └── init.sql
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── Makefile
├── package.json                # Tailwind CSS e plugins
├── tailwind.config.js
├── pyproject.toml              # ruff, mypy, pytest
└── .env.example
```

---

## Arquitetura

### Monólito Modular

SafraLog usa **monólito modular Django** — um único processo com apps bem delimitados. Não há microserviços.

```
┌─────────────────────────────────────────┐
│              Django App                  │
│                                          │
│  operations │ logistics │ finance        │
│  dashboard  │ accounts  │ notifications  │
│  attachments│ reports   │ tenants        │
└─────────────────────────────────────────┘
        │                    │
   PostgreSQL             Redis
   (dados + sessions)   (cache + Celery)
```

### Multi-tenant

Isolamento por **Foreign Key** — todas as queries incluem `tenant=request.tenant`. O `TenantMiddleware` injeta o tenant em `request.tenant` a partir do usuário autenticado.

```python
# Todas as queries protegidas automaticamente
Waybill.objects.filter(tenant=request.tenant, ...)
```

### Ledger Financeiro

Inspirado em double-entry bookkeeping — toda movimentação gera uma `LedgerEntry` **imutável**. Nunca se faz UPDATE ou DELETE em entradas do ledger. Estornos criam contra-entradas.

```
Romaneio confirmado → LedgerEntry(type=CREDIT, amount=+R$1.200)
Abastecimento       → LedgerEntry(type=DEBIT,  amount=−R$320)
Adiantamento        → LedgerEntry(type=DEBIT,  amount=−R$500)
                                              ──────────────
Saldo = SUM(LedgerEntry.amount)             =  R$380
```

### HTMX + Django Templates

Interatividade sem SPA. O servidor renderiza HTML; o HTMX atualiza partes da página.

```
Filtro de romaneios → GET /romaneios/?status=confirmed
                           ↓ (hx-target="#waybill-table")
                      Retorna só o <tbody> — sem reload
```

### Auditoria

Toda alteração em modelos críticos é registrada via `django-simple-history`:

```python
class Waybill(AuditedModel):
    # AuditedModel herda HistoricalRecords
    # Cada save gera um snapshot em operations_historicalwaybill
    # Com: usuário, timestamp, IP, antes/depois
```

---

## Variáveis de ambiente

### Obrigatórias em produção

```bash
DJANGO_SECRET_KEY=          # Mínimo 50 caracteres, aleatório
DJANGO_SETTINGS_MODULE=config.settings.production
DATABASE_URL=               # postgresql://user:pass@host:5432/db
REDIS_URL=                  # redis://host:6379/0
CELERY_BROKER_URL=          # redis://host:6379/1

# Storage S3
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_REGION_NAME=sa-east-1

# Segurança
DJANGO_ALLOWED_HOSTS=seu-dominio.com.br
DJANGO_CSRF_COOKIE_SECURE=True
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_SECURE_SSL_REDIRECT=True
```

### Opcionais

```bash
SENTRY_DSN=                 # Monitoramento de erros
EMAIL_HOST=                 # SMTP para envio de emails
FLOWER_USER=admin           # Auth do Flower
FLOWER_PASSWORD=
```

---

## Testes

```bash
# Todos os testes
make test

# App específico
make test-app APP=operations

# Com cobertura (gera relatório HTML em htmlcov/)
make test-coverage

# Rápido — para na primeira falha
make test-fast
```

### Convenções

- Testes ficam em `tests/` e em `apps/<app>/tests/`
- Factories em `tests/factories/` usando `factory-boy`
- Fixtures de banco via `pytest-django` com `@pytest.mark.django_db`
- Mocks de tempo via `time-machine`

```python
# Exemplo
@pytest.mark.django_db
def test_waybill_net_weight(waybill_factory):
    wb = waybill_factory(gross_weight=50000, tare_weight=14000)
    assert wb.net_weight == 36000
    assert wb.net_weight_tons == Decimal("36.000")
```

---

## Deploy

### VPS Hostinger — Configuração (Produção)

**Servidor:** `147.93.15.214` — Ubuntu 24.04, Docker  
**Domínio:** `safralog.ferzion.com.br`  
**Porta interna:** `127.0.0.1:8120` (Gunicorn)  
**Diretório:** `/var/www/docker-instances/SafraLog/`

> **Regra crítica:** O servidor já tem nginx do HOST gerenciando 80/443 para outros 10 sistemas. O container do SafraLog NUNCA expõe as portas 80 ou 443.

#### Deploy automatizado

```bash
# No VPS, dentro do diretório do projeto:
./scripts/deploy_vps.sh
```

O script faz automaticamente:
1. Valida `.env.production`
2. Verifica ausência de conflito de portas 80/443
3. Compila CSS + copia bundles JS (HTMX, Alpine, ApexCharts)
4. Build e sobe containers Docker (`127.0.0.1:8120:8000`)
5. Aplica migrations
6. Coleta estáticos em `/var/www/docker-instances/SafraLog/static_collected/`

#### Configuração do nginx (host)

```bash
# Copiar config
sudo cp docker/nginx/safralog.ferzion.com.br.conf \
        /etc/nginx/sites-available/safralog.ferzion.com.br

# Ativar
sudo ln -s /etc/nginx/sites-available/safralog.ferzion.com.br \
           /etc/nginx/sites-enabled/safralog.ferzion.com.br

# Obter SSL
sudo certbot certonly --nginx -d safralog.ferzion.com.br

# Testar e recarregar
sudo nginx -t && sudo systemctl reload nginx
```

#### Primeira vez no servidor

```bash
# Criar superusuário
docker compose exec django python manage.py createsuperuser

# Criar o tenant (grupo de produtores)
docker compose exec django python manage.py shell -c "
from apps.tenants.models import Tenant
Tenant.objects.create(name='Grupo de Produtores', slug='grupo', status='active')
"
```

#### Variáveis críticas para produção

Preencher em `.env.production` antes do deploy:

```bash
DJANGO_SECRET_KEY          # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DJANGO_ALLOWED_HOSTS       # safralog.ferzion.com.br,147.93.15.214
DATABASE_URL               # postgresql://safralog_user:SENHA@postgres:5432/safralog
POSTGRES_PASSWORD          # Senha do banco
EMAIL_HOST_USER            # Email para notificações
EMAIL_HOST_PASSWORD        # Senha do email
```

---

## Contribuindo

1. Crie uma branch: `git checkout -b feat/nome-da-feature`
2. Rode o linter antes de commitar: `make lint`
3. Garanta que os testes passam: `make test`
4. Abra um Pull Request com descrição clara do que foi feito

### Padrões de código

- **Python**: PEP 8 via Ruff, type hints onde possível
- **Django**: class-based views, sem lógica de negócio nas views (use services/selectors)
- **Templates**: componentes pequenos, HTMX para interatividade, sem JavaScript desnecessário
- **SQL**: sempre `select_related`/`prefetch_related` para evitar N+1; `output_field` explícito em `Coalesce` com tipos mistos

---

## Licença

Proprietário — SafraLog © 2026. Todos os direitos reservados.
