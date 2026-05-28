# SafraLog — Roadmap do Projeto

> Sistema SaaS de logística e financeiro agrícola.
> Stack: Django 5.1 · PostgreSQL 16 · HTMX · Alpine.js · TailwindCSS · Docker · Redis · Celery · ApexCharts

---

## Ambiente de Desenvolvimento

```bash
# Subir containers
docker compose -f infrastructure/docker-compose.yml \
               -f infrastructure/docker-compose.dev.yml up -d

# Build CSS + coleta estáticos
npm run build && make static && make check

# Testes
make test-fast      # 255/255, 0 warnings
make test-coverage  # 72.05% cobertura

# URLs
App:    http://localhost:8000
Admin:  http://localhost:8000/admin
Flower: http://localhost:5555
Mail:   http://localhost:8025
```

**Credenciais dev:**
- `admin@safralog.dev` / `admin123` (role: admin)
- `gerente@safralog.dev` / `gerente123` (role: manager)
- `operador@safralog.dev` / `op123` (role: operator)

**Dados de demo:**
- Tenant: "Fazenda Santa Fé Demo" (slug: fazenda-demo, plan: professional)
- Safra ativa: "Safra Soja 2024/25" (soybean)
- 7 motoristas, 5 veículos, 5 talhões, 61 romaneios (mixed statuses)

> **ATENÇÃO:** O seed script criou romaneios com `status=CONFIRMED` diretamente,
> bypassando `WaybillConfirmView`. Logo, `LedgerEntry` de crédito (`waybill_production`)
> **não existe** para esses romaneios. O `faturamento_bruto` no dashboard é calculado
> direto dos `Waybill` (`gross - tare) * unit_price / 1000`), não do `LedgerEntry`.
> Isso é **intencional** — o selector tolera ambos os cenários.

---

## Status Geral

| Camada | Status |
|---|---|
| Infraestrutura Docker | ✅ Completo |
| Models + Migrations | ✅ Completo |
| Autenticação + Autorização | ✅ Completo |
| Seed de dados dev | ✅ Completo |
| CSS / Assets pipeline | ✅ Completo |
| Dashboard — BI completo | ✅ Completo |
| Dashboard — Quick search HTMX | ✅ Completo (Sessão 9) |
| Romaneios — CRUD + Ledger + Cancelamento | ✅ Completo (Sessão 8) |
| Motoristas | ✅ Completo |
| Safras | ✅ Completo |
| Talhões | ✅ Completo |
| Veículos | ✅ Completo |
| Abastecimentos | ✅ Completo |
| Adiantamentos | ✅ Completo |
| Fechamentos + Settlement Service | ✅ Completo (Sessão 8) |
| Ledger (service + model) | ✅ Completo (Sessão 8) |
| Notificações — signals + tasks + Beat | ✅ Completo (Sessão 9) |
| Notificações — dropdown browser validado | ✅ Completo (Sessão 11) |
| Middlewares — core + tenants | ✅ Completo (Sessão 10) |
| Template tags (Decimal) | ✅ Completo |
| base.html + partials | ✅ Completo |
| Sidebar + Navbar | ✅ Completo |
| URLs completas | ✅ Completo |
| PDFs (WeasyPrint) — views + templates | ✅ Completo (Sessão 9) |
| PDFs — validado no browser | ✅ Completo (Sessão 11) |
| Logo PNG — 256×256px, 33KB | ✅ Completo (Sessão 11) |
| Uploads — compressão Canvas API | ✅ Completo (Sessão 9) |
| Settings — base.py + production.py | ✅ Completo (Sessão 9) |
| Páginas de erro (403, 404, 500) | ✅ Completo |
| `make check` — 0 issues | ✅ Completo |
| Testes — 255/255, 0 warnings | ✅ Completo (Sessão 12) |
| Cobertura — 72.05% (meta 65% ✅) | ✅ Completo (Sessão 12) |
| `pyproject.toml` — coverage fix | ✅ Completo (Sessão 10) |
| `tasks.py` — refatorado (cache admins + dedup seen) | ✅ Completo (Sessão 11) |
| `UserFactory` — username único via Sequence | ✅ Completo (Sessão 12) |
| ApexCharts — movido para bundle local | ✅ Completo (Sessão 12) |
| Auditoria de templates (roadmap-frontend) | 🟡 Em andamento (Sessão 12) |
| Model Proprietário (dono do caminhão) | ✅ Completo (Sessão 14) |
| Model Região (preço por tonelada) | ✅ Completo (Sessão 14) |
| Fueling: preço duplo + extras_amount | ✅ Completo (Sessão 14) |
| Settlement: status PAID + comprovante + custom_overrides | ✅ Completo (Sessão 15) |
| base.html exclusivo do SafraLog | ✅ Completo (Sessão 15) |
| HTMX + Alpine.js → bundles locais (npm) | ✅ Completo (Sessão 15) |
| Deploy VPS Hostinger (safralog.ferzion.com.br:8120) | ✅ Configurado (Sessão 15) |
| Multi-tenant SaaS (UI) | 🔴 Não necessário (uso interno) |

---

## 1. Infraestrutura e DevOps ✅

- [x] Docker Compose (base + dev + prod), Dockerfile multi-stage
- [x] Makefile completo
- [x] `make check` → 0 issues
- [x] ApexCharts movido do CDN para bundle local (`package.json`)

### Atenção
- [ ] `npx update-browserslist-db@latest` — warn residual no build

---

## 2. Configurações Django ✅

- [x] Settings split completo: `base.py` / `development.py` / `production.py` / `testing.py`
- [x] `CELERY_BEAT_SCHEDULE` com `low_priority` queue
- [x] `production.py` — HTTPS, HSTS, S3, Sentry, file logging, checklist deploy

---

## 3. Models e Banco de Dados ✅

- [x] Todos os models com migrations, índices e constraints
- [x] `@transaction.atomic` em `LedgerEntry.create_reversal()`

### Atenção
- [ ] Índice composto `(tenant, operation_date)` em `Waybill` — migration pendente
- [ ] Constraint `unique_active_harvest_per_tenant` — verificar migration

---

## 4–11. Autenticação, Dashboard, Operações, Logística ✅

Todos completos. Sem débitos críticos.

---

## 12–14. Financeiro ✅

- [x] Ledger com `create_reversal()` atômico
- [x] Fechamentos: fluxo completo `create→submit→approve→close→cancel`
- [x] Adiantamentos: `confirm()` e `cancel()` com ledger integrado

### Falta
- [ ] Extrato do motorista (PDF)

---

## 15. Anexos e Uploads ✅

- [x] Compressão Canvas API — foto 4MB → ~250KB

### Falta
- [ ] Upload S3 em produção

---

## 16. Notificações ✅

- [x] Celery Beat rodando — crontab 06h (`check_negative_balances`) e 07h (`check_cnh_expiry`) BRT
- [x] Dropdown no browser validado — badge, lista HTMX, "marcar lidas"
- [x] `tasks.py` refatorado — cache de admins por tenant, `seen` set anti-duplicata, `balance >= 0` guard restaurado
- [x] 4 notificações de saldo negativo geradas e exibidas corretamente nos dados de demo

> **Diagnóstico Sessão 11:**
> - Beat só mostra `Writing entries` (normal) — tasks disparam no horário configurado
> - `DJANGO_SETTINGS_MODULE` no container é `config.settings.development` (não `safralog.*`)
> - Apps ficam em `apps/` — usar `from apps.notifications.models import Notification` no shell
> - "Duplicatas" no banco eram notificações para usuários distintos (admin + manager) — comportamento correto
> - `current_balance` é `@property` Python — não filtrável via ORM (`FieldError`)

---

## 17. PDFs e Relatórios ✅ (código) / ✅ (validação)

- [x] `waybill.html`, `settlement.html`, `waybill_list.html` — todos corrigidos
- [x] Validados no browser

### Falta
- [ ] Extrato do motorista
- [ ] CSV export

---

## 20. Testes ✅

**Estado: 255 testes / 0 falhas / 0 warnings — Sessão 12**
**Cobertura: 72.05%**

| Arquivo | Testes | Cobertura módulo |
|---|---|---|
| `test_waybill.py` | 9 | waybill model + views |
| `test_waybill_cancel.py` | 15 | cancel + reversal + confirm |
| `test_settlement.py` | 20 | fluxo completo fechamento |
| `test_settlement_views.py` | 20 | settlement views (91%) |
| `test_advance.py` | 14 | advance model 100% |
| `test_template_tags.py` | 37 | core_tags 86% |
| `test_selectors.py` | 55 | dashboard selectors 92% |
| `test_tasks.py` | 19 | notifications tasks 94% |
| `test_middleware.py` | 27 | core middleware 100%, tenants 95% |
| `test_ledger_service.py` | 5 | ledger_service 87% |
| `test_settlement_service.py` | 4 | settlement_service 98% |

**Cobertura por módulo (destaque):**

| Módulo | Cover |
|---|---|
| `core/middleware.py` | 100% |
| `finance/models/advance.py` | 100% |
| `core/mixins.py` | 100% |
| `finance/services/settlement_service.py` | 98% |
| `finance/models/ledger.py` | 98% |
| `notifications/tasks.py` | 94% |
| `tenants/middleware.py` | 95% |
| `dashboard/selectors.py` | 92% |
| `finance/views/settlement.py` | 91% |

**Cobertura por módulo (descobertos — oportunidades):**

| Módulo | Cover | Linhas miss |
|---|---|---|
| `attachments/views.py` | 22% | 45 |
| `core/context_processors.py` | 24% | 34 |
| `reports/views/pdf.py` | 24% | 47 |
| `logistics/views/fueling.py` | 33% | 46 |
| `operations/views/harvest.py` | 33% | 48 |
| `finance/views/advance.py` | 38% | 42 |
| `logistics/views/driver.py` | 36% | 53 |

**`pyproject.toml` — coverage config:**
- `data_file = "/tmp/.coverage"` — fix de permissão no container
- `fail_under = 65` — meta progressiva (atingimos 72.05%)
- `[tool.coverage.html] directory = "/tmp/htmlcov"`

### Falta para 75%+
- [ ] `attachments/views.py` — 22% (45 linhas miss)
- [ ] `core/context_processors.py` — 24% (34 linhas miss)
- [ ] `logistics/views/driver.py` — 36% (53 linhas miss)
- [ ] `finance/views/advance.py` — 38% (42 linhas miss)

---

## 18. Frontend — Auditoria e Qualidade de Templates 🟡

> Iniciado na Sessão 12. Ver **roadmap-frontend.md** para detalhes completos.

- [ ] Auditoria de todos os HTMLs (comentários, bugs, acessibilidade, HTMX)
- [ ] Padronização de componentes (cards, tabelas, formulários, badges)
- [ ] Revisão de mensagens e labels em PT-BR
- [ ] Validação de fallbacks HTMX e Alpine.js
- [ ] Zero comentários de debug nos templates de produção

---

## 21. Multi-tenant SaaS 🔴

- [x] Arquitetura completa (queries filtradas, middleware)
- [ ] Signup/onboarding flow
- [ ] Planos e trial
- [ ] `max_users` enforcement
- [ ] Página de suspensão
- [ ] S3 com prefix por tenant

---

## Próximos Passos — Prioridade

### ✅ Concluído — pronto para deploy

Todos os itens críticos de deploy estão resolvidos. Sistema pode ser publicado em `safralog.ferzion.com.br`.

**Deploy:** `./scripts/deploy_vps.sh` no VPS, seguido de configuração do nginx e certbot.

### 🟡 Qualidade — em andamento

| # | Tarefa | Ganho | Status |
|---|---|---|---|
| 1 | Auditoria templates HTML (32 de 49 restantes) | UX + zero bugs visuais | 🟡 Em andamento |
| 2 | Testes para novos models (Proprietario, Region, Settlement.paid) | Cobertura → 75%+ | 🔴 Pendente |
| 3 | Filtro de período no dashboard (HTMX) | UX operacional | 🔴 Pendente |
| 4 | Extrato do motorista (PDF) | Completude de relatórios | 🔴 Pendente |
| 5 | CSV export | Alternativa ao PDF | 🔴 Pendente |
| 6 | Recalcular snapshot_data ao usar custom_overrides | Consistência do PDF | 🔴 Pendente |

### 🟢 Fase Final — Melhorias pós-deploy

| # | Tarefa |
|---|---|
| 7 | Validar SSL + HTTPS no VPS |
| 8 | Storage S3 (atualmente filesystem local) |
| 9 | Sentry DSN para monitoramento de erros |
| 10 | Seed de dados reais de produção |

---

## Bugs e Débitos Conhecidos

| Prioridade | Descrição | Arquivo |
|---|---|---|
| 🟡 Média | `browserslist` desatualizado | host |
| 🟢 Baixa | Índice composto `(tenant, operation_date)` em `Waybill` | migration pendente |
| 🟢 Baixa | CSV export como alternativa ao PDF | `apps/reports/` |
| 🟢 Baixa | Extrato financeiro do motorista | `apps/reports/` |

---

## Padrões Obrigatórios — Referência Rápida

### Coalesce com Decimal
```python
from decimal import Decimal
from django.db.models import DecimalField
_ZERO = Decimal("0")
Coalesce(Sum("gross_weight"), _ZERO, output_field=DecimalField())
net_tons = (gross - tare) / Decimal("1000")
```

### Testes de view (RequestFactory)
```python
def test_list(self, rf, admin_user, tenant):
    request = rf.get("/")
    request.user = admin_user
    request.tenant = tenant
    response = MyView.as_view()(request)
    assert response.status_code == 200
```

### Http404 em testes de view
```python
# Views com get_object_or_404 filtrado por status levantam Http404
# — não retornam response.status_code == 404 via RequestFactory
from django.http import Http404
with pytest.raises(Http404):
    MyView.as_view()(request, pk=pk)
```

### Patch de cache em middleware
```python
# cache é importado dentro do método — patch no módulo real
with patch("django.core.cache.cache") as mock_cache:
    ...
```

### Fluxo de fechamento
```python
create_settlement()    # → DRAFT
submit_settlement()    # → PENDING_APPROVAL
approve_settlement()   # → APPROVED (approved_by, approved_at)
# Opcional: editar custom_overrides antes de pagar (HTMX overlay no detalhe)
mark_paid()            # → PAID (payment_date, payment_proof, paid_by, paid_at)
close_settlement()     # → CLOSED (closed_at) — legado
cancel_settlement()    # qualquer status exceto PAID/CLOSED
```

### Compressão de upload
```javascript
const compressed = await compressImage(file, { maxWidth: 1920, quality: 0.82, maxSizeKB: 600 });
```

### Shell no container
```bash
# DJANGO_SETTINGS_MODULE = config.settings.development (não safralog.*)
# Apps ficam em apps/ — sempre usar prefixo completo:
docker compose -f infrastructure/docker-compose.yml \
               -f infrastructure/docker-compose.dev.yml exec django bash -c '
python manage.py shell -c "from apps.notifications.models import Notification; ..."'
```

### Disparar task Celery manualmente
```bash
docker compose -f infrastructure/docker-compose.yml \
               -f infrastructure/docker-compose.dev.yml exec django bash -c '
python manage.py shell -c "
from celery import current_app
current_app.send_task(\"notifications.check_negative_balances\", queue=\"low_priority\")
"'
```

---

## Decisões de Arquitetura

| Decisão | Motivo |
|---|---|
| `faturamento_bruto` via Waybill (não LedgerEntry) | Seed bypass — LedgerEntry pode não existir |
| `SimpleNamespace` como proxy no dashboard | Templates precisam de atributos em PT |
| `SESSION_ENGINE = 'db'` em dev | allauth `cycle_key()` invalida session em cache |
| `settlement_service` com `snapshot_data` | PDF nunca depende de dados vivos após fechamento |
| `Decimal` em todo o financeiro | Float tem erros de precisão binária |
| `RequestFactory` com `_messages` patch | Bypassa middleware — sem patch lança `MessageFailure` |
| `select_for_update` removido do `_cancel_atomic` | Incompatível com wrapping de transação do pytest-django |
| `@transaction.atomic` em `create_reversal` | Par INSERT+UPDATE deve ser atômico |
| `submit_settlement()` separado de `create_settlement()` | Criação e envio são atos distintos |
| `base_url=MEDIA_ROOT` no WeasyPrint | Resolve imagens via `file://` sem servidor HTTP |
| `compressImage()` antes do XHR | 4MB → ~250KB — crítico para 3G rural |
| `check_negative_balances` filtra `account_type=DRIVER` | Evita varrer contas operacionais |
| `current_balance` é `@property` — não filtrável via ORM | Usar `if balance >= 0: continue` em Python |
| Cache de admins por tenant em tasks | Evita N+1 de queries em loops com múltiplos drivers |
| `seen` set em `check_negative_balances` | Guard contra 2 FinancialAccount para o mesmo driver |
| File handler de logging só em `production.py` | Container não tem permissão em `/app/logs` |
| `crontab` import no topo de `base.py` | Import no meio quebrava o Celery beat |
| `data_file = "/tmp/.coverage"` | Container não tem permissão de escrita em `/app/` |
| `Http404` com `pytest.raises` em view tests | `RequestFactory` não processa middleware de exceções |
| `get_tenant()` testada diretamente (não via `SimpleLazyObject`) | `SimpleLazyObject` wrapping `None` nunca é `None` — força avaliação explícita |
| `FinancialAccountFactory.account_type = "driver"` | Tasks filtram por `account_type=DRIVER` — sem isso tasks não encontravam contas |
| Navbar inline em `base.html` | `{% block %}` não funciona em `{% include %}` |
| `__str__` sem FK em Waybill | `str(waybill)` em loops causava N+1 via `driver` |
| `UserFactory.username` via `Sequence` | Django exige username único — sem Sequence gerava `""` duplicado |
| ApexCharts via bundle local | CDN falha em campo rural sem internet (3G instável) |

---

*Atualizado em: 28/05/2026 — Sessão 14–15: Proprietário (dono do caminhão), Região (preço/ton), preço duplo no abastecimento (driver_price_per_liter + posted_price_per_liter + extras_amount), Settlement.status=PAID + comprovante + custom_overrides para ajuste de valores, base.html exclusivo do SafraLog, deploy configurado para safralog.ferzion.com.br:8120 no VPS Hostinger.*
