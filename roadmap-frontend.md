# SafraLog — Roadmap Frontend (Sessão 12+)

> Auditoria e qualidade de todos os 49 templates HTML.
> Objetivo: zero bugs visuais, zero comentários de debug, PT-BR consistente,
> HTMX/Alpine.js corretos, acessibilidade mínima e UX coerente em todos os módulos.

---

## Critérios de Auditoria — Checklist Universal

| # | Critério | Descrição |
|---|---|---|
| C1 | **Comentários de debug** | Nenhum `<!-- TODO -->`, `<!-- FIXME -->`, `<!-- teste -->` ou comentário temporário em produção |
| C2 | **Extends/blocks corretos** | `{% extends %}` aponta para o base certo; todos os `{% block %}` abertos são fechados |
| C3 | **PT-BR consistente** | Labels, placeholders, mensagens de erro e textos de interface em português correto |
| C4 | **HTMX íntegro** | `hx-target`, `hx-swap`, `hx-trigger`, `hx-indicator` presentes onde necessário; sem atributos soltos |
| C5 | **Alpine.js íntegro** | `x-data`, `x-show`, `x-bind`, `@click` sem referências a variáveis inexistentes |
| C6 | **Links e URLs** | Apenas `{% url %}` — zero URLs hardcoded; nenhum `href="#"` funcional sem handler |
| C7 | **Estados vazios** | Todo list/table tem `{% empty %}` ou bloco de estado vazio com mensagem útil |
| C8 | **Feedback de ação** | Forms têm mensagens de sucesso/erro via `messages` ou HTMX response |
| C9 | **Acessibilidade mínima** | `<label>` vinculado ao `<input>` via `for`/`id`; botões têm texto ou `aria-label` |
| C10 | **Consistência visual** | Classes Tailwind seguem o padrão do sistema (sem classes inline únicas sem motivo) |
| C11 | **Variáveis seguras** | Uso de `{{ var\|default:"" }}` ou `{% if var %}` antes de renderizar FKs e opcionais |
| C12 | **PDFs separados** | Templates de PDF não herdam `base.html`; têm CSS inline próprio |

---

## Fase A — Base e Partials ✅ Concluída (Sessão 12)

---

### `base.html`

**Função:** Esqueleto HTML de toda a aplicação autenticada. Define o layout de duas
colunas (sidebar + área principal), monta o header inline com título da página, botão
de ação principal, dropdown de notificações e alternância de dark mode. Injeta HTMX,
Alpine.js e os scripts globais.

**O que o usuário faz nesta tela:**
- Navega por qualquer tela do sistema (envolve todos os outros templates)
- Abre/fecha a sidebar em dispositivos mobile
- Alterna entre dark mode e light mode (persiste via localStorage)
- Abre o dropdown de notificações e marca como lidas
- Vê o título da seção atual e aciona o botão de ação principal

**Funções futuras a implementar:**
- [ ] Atalho de teclado global `Ctrl+K` para busca rápida
- [ ] Banner de aviso de trial expirando (ex: "Seu plano expira em 3 dias")
- [ ] Indicador de plano/quota no header (ex: "Starter · 3/10 usuários")

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | `{% comment %}` é documentação arquitetural válida |
| C4 | ✅ | `hx-headers` com CSRF no `<body>`, `hx-ext` declarado |
| C5 | ✅ | `x-data` no `<html>` com `sidebarOpen` e `darkMode` corretos |
| C6 | ⚠️ | HTMX, Alpine e loading-states ainda carregam de CDN (`unpkg`) |
| C9 | ✅ | Todos os botões têm `aria-label` |
| C10 | ✅ | |

**Bugs corrigidos:**
- 🔴 **BUG #1 — CDN offline:** HTMX 2.0.4, Alpine 3.14.3 e htmx-ext-loading-states
  carregavam de `unpkg.com`. Em campo rural sem internet, toda interatividade parava.
  Migrado para bundles locais via `package.json` (igual ao ApexCharts).
- 🔴 **BUG #2 — "Marcar lidas" ausente:** O dropdown de notificações inline não tinha
  o botão "Marcar lidas" que existia corretamente em `navbar.html`. A funcionalidade
  estava implementada mas nunca chegou ao template real. Mesclado da versão correta.

---

### `partials/navbar.html`

**Função:** Arquivo **legado — não renderizado em nenhuma view**. Continha a versão
mais completa do dropdown de notificações (com "Marcar lidas") e dark mode toggle.
O conteúdo foi absorvido inline em `base.html` por limitação do Django (`{% block %}`
não funciona dentro de `{% include %}`), mas de forma incompleta.

**O que o usuário faz nesta tela:** N/A — arquivo não renderizado.

**Resultado da auditoria:**
- Marcado com aviso de deprecação no topo do arquivo.
- Conteúdo correto mesclado em `base.html`.
- Mantido como referência histórica.

---

### `partials/sidebar.html`

**Função:** Barra lateral de navegação global. Exibe logo + nome do tenant, campo de
busca rápida (HTMX com debounce 400ms), links agrupados por módulo (Operações,
Logística, Financeiro, Relatórios) e o menu do usuário com avatar, nome, cargo, link
para perfil e logout.

**O que o usuário faz nesta tela:**
- Navega entre todos os módulos do sistema com um clique
- Usa a busca rápida sem sair da tela atual
- Confirma em qual tenant está logado
- Acessa o perfil ou faz logout pelo menu do avatar

**Funções futuras a implementar:**
- [ ] Badge de pendências nos links de navegação (ex: "Romaneios · 5 pendentes")
- [ ] Indicador da safra ativa abaixo do nome do tenant
- [ ] Seção de administração visível apenas para admin/manager

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C5 | ✅ | Alpine `open` + `keydown.escape` corretos |
| C6 | ✅ | Todos os links via `{% url %}` |
| C9 | ✅ | `aria-label="Busca rápida"` adicionado ao input |
| C10 | ✅ | |
| C11 | ✅ | `avatar` verificado antes de renderizar |

**Melhoria aplicada:**
- 🟡 **MELHORIA #1 — Acessibilidade:** `aria-label="Busca rápida"` adicionado ao `<input>` de busca. `aria-hidden="true"` nos SVGs decorativos.

---

### `partials/messages.html`

**Função:** Sistema de toasts (flash messages Django). Renderiza notificações de
sucesso, erro, aviso e info no canto superior direito da tela. Auto-fecha em 5 segundos
com barra de progresso animada. Fechável manualmente pelo botão X.

**O que o usuário faz nesta tela:**
- Lê o resultado de ações (ex: "Romaneio confirmado com sucesso")
- Fecha o toast manualmente antes do auto-fechamento
- Percebe visualmente o tipo de mensagem pela cor e ícone

**Funções futuras a implementar:**
- [ ] Toast via JavaScript para respostas HTMX sem redirect (atualmente só aparece
  após redirect com `messages.add_message()` na view)

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C3 | ✅ | |
| C8 | ✅ | Cobre success/error/warning/info |
| C9 | ✅ | `role="alert"`, `aria-label` no botão fechar |
| C10 | ✅ | |

**Bug corrigido:**
- 🔴 **BUG #4 — `absolute` sem `relative` pai:** A barra de progresso usava
  `position: absolute` mas o card do toast não tinha `position: relative`.
  O elemento se ancorava no container `fixed` pai e aparecia fora do card.
  **Fix:** adicionado `relative` ao `<div>` de cada toast individual.

**Atenção remanescente:**
- `animate-[shrink_5s_linear_forwards]` requer `@keyframes shrink` em `tailwind.config.js`.
  Verificar se está definido; sem ele a barra de progresso fica estática.

---

### `partials/pagination.html`

**Função:** Componente de paginação reutilizável para todas as listagens. Exibe
contagem total de registros, botões anterior/próximo e uma janela de páginas (±2 da
atual, sempre mostrando a primeira e a última). Suporta HTMX e query string opcionais.

**O que o usuário faz nesta tela:**
- Navega entre páginas de listagens longas
- Confirma quantos registros existem no total e em qual página está

**Funções futuras a implementar:**
- [ ] Seletor "registros por página" (10 / 25 / 50) com HTMX
- [ ] Input "ir para página X" para listas muito longas

**Resultado da auditoria:** ✅ **Sem bugs. Aprovado sem alterações.**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | Comentário inline é explicação de lógica válida |
| C3 | ✅ | "Ant." / "Próx." em PT-BR |
| C6 | ✅ | Sem URLs hardcoded |
| C9 | ✅ | `aria-label="Paginação"` na nav |
| C10 | ✅ | |

---

### `base_modal.html`

**Função:** Template base reutilizável para modais carregados via HTMX no
`#modal-container` do `base.html`. Define estrutura padrão com header (título + fechar),
body e footer opcional. Funciona como `{% extends "base_modal.html" %}` em qualquer
template parcial de modal.

**O que o usuário faz nesta tela:**
- Interage com qualquer modal do sistema (confirmações, formulários inline, detalhes)
- Fecha clicando no X, no overlay escuro ou com Escape

**Funções futuras a implementar:**
- [ ] Suporte a tamanhos via bloco ou classe (sm / md / lg / xl)
- [ ] Confirmação de saída se o formulário foi modificado (`x-data` com flag `dirty`)

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | Bloco de comentário é documentação de uso válida |
| C2 | ✅ | Blocks `modal_title`, `modal_body`, `modal_footer` corretos |
| C5 | ✅ | `closeModal()` centralizado; `@keydown.window.escape` adicionado |
| C9 | ✅ | `aria-label="Fechar"` no botão X |
| C10 | ✅ | |

**Melhorias aplicadas:**
- 🟡 **MELHORIA #1:** `aria-label="Fechar"` adicionado ao botão X.
- 🟡 **MELHORIA #2:** Lógica de fechar/limpar `modal-container` extraída para
  função Alpine `closeModal()` — evita duplicação entre overlay e botão X.
- 🟡 **MELHORIA #3:** `@keydown.window.escape` adicionado para fechar com Escape.
- 🟡 **MELHORIA #4:** `x-transition` adicionado ao overlay — o fundo agora anima
  junto com o panel ao fechar (bug extra: overlay sumia sem animação).

---

## Resumo da Fase A

| Template | Bugs críticos | Melhorias | Status final |
|---|---|---|---|
| `base.html` | 2 corrigidos | — | ✅ Corrigido |
| `partials/navbar.html` | 1 (órfão mesclado) | — | ✅ Deprecated |
| `partials/sidebar.html` | — | 1 (aria-label) | ✅ Corrigido |
| `partials/messages.html` | 1 (relative ausente) | 1 (keyframes atenção) | ✅ Corrigido |
| `partials/pagination.html` | — | — | ✅ Aprovado |
| `base_modal.html` | — | 4 (aria, ESC, fn, overlay) | ✅ Corrigido |

**Total Fase A: 4 bugs corrigidos · 6 melhorias aplicadas**

---

## Fase B — Fluxo Principal ✅ Concluída (Sessão 13)

---

### Grupo 6 — Romaneios ✅ Concluído

---

### `operations/waybill/list.html`

**Função:** Listagem paginada de romaneios com filtros combinados de status, motorista
e período de datas. A tabela (`#waybill-table`) é atualizada via HTMX sem reload de
página. Botão "Novo" visível apenas em telas `sm+`.

**O que o usuário faz nesta tela:**
- Filtra romaneios por status, motorista e intervalo de datas
- Busca por texto livre (número, nome do motorista)
- Navega pelas páginas de resultados
- Acessa o detalhe de um romaneio
- Cria um novo romaneio

**Funções futuras a implementar:**
- [ ] Botão flutuante "Novo" no mobile (substituir o `hidden sm:flex`)
- [ ] Exportar listagem filtrada como PDF ou CSV
- [ ] Totalizador de tonelagem e valor na barra de resumo

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks `title`, `nav_title`, `quick_action`, `content` fechados |
| C3 | ✅ | |
| C4 | ✅ | `hx-indicator="#global-loading"` adicionado; trigger corrigido |
| C6 | ✅ | Todos os links via `{% url %}` |
| C7 | ✅ | Estado vazio tratado em `_table.html` |
| C9 | ✅ | `aria-label` e `<label class="sr-only">` em todos os campos de filtro |
| C10 | ✅ | |

**Bugs corrigidos:**
- 🔴 **BUG #1 — C4 — `hx-trigger` não cobre datas:** O trigger era
  `change from:select, keyup changed delay:400ms from:input[name=q]`. Alterar as
  datas de filtro não disparava atualização da tabela — o usuário trocava o período
  e nada acontecia.
  **Fix:** adicionado `change from:input[type=date]` ao trigger.
- 🔴 **BUG #2 — C9 — Campos de filtro sem label:** Os 5 campos (`q`, `status`,
  `driver`, `date_start`, `date_end`) não tinham `<label>` nem `aria-label` —
  invisíveis para leitores de tela.
  **Fix:** `<label class="sr-only">` + `aria-label` adicionados a todos.

**Melhoria aplicada:**
- 🟡 **MELHORIA #1 — C4:** `hx-indicator="#global-loading"` adicionado ao form —
  referência explícita à barra de loading global para feedback visual durante filtragem.

---

### `operations/waybill/form.html`

**Função:** Formulário unificado para criação e edição de romaneio. Dividido em
quatro seções: Operação (safra, talhão, data, hora, cultura), Logística (motorista,
veículo), Pesagem (bruto, tara, preço/t, ticket) e Destino (armazém, notas).
Exibe erros de campo e erros globais do form.

**O que o usuário faz nesta tela:**
- Preenche os dados do romaneio (criação ou edição)
- Corrige erros de validação destacados por campo
- Cancela e volta ao detalhe ou à listagem

**Funções futuras a implementar:**
- [ ] Cálculo em tempo real de peso líquido e valor total (Alpine.js reativo)
- [ ] Filtro de talhão dependente da safra selecionada (HTMX `hx-get` ao trocar safra)
- [ ] Filtro de veículo dependente do motorista selecionado

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks fechados |
| C3 | ✅ | |
| C6 | ✅ | |
| C8 | ✅ | Erros de campo e `non_field_errors` tratados |
| C9 | ✅ | `for="{{ form.CAMPO.id_for_label }}"` adicionado a todos os 13 labels |
| C10 | ✅ | |
| C11 | ✅ | Link "Cancelar" guarda `waybill` com `{% if waybill %}` |

**Bug corrigido:**
- 🔴 **BUG #3 — C9 — Labels sem `for`:** Todos os 13 `<label>` usavam
  `class="label"` mas não tinham atributo `for`. Clicar em qualquer label não focava
  o campo correspondente; leitores de tela não associavam label ao input.
  **Fix:** `for="{{ form.CAMPO.id_for_label }}"` adicionado a todos os labels.
  Aproveitado para adicionar `{% if form.CAMPO.errors %}` nos campos que ainda não
  tinham tratamento de erro (`operation_time`, `scale_ticket`, `destination`, `notes`).

---

### `operations/waybill/detail.html`

**Função:** Detalhe completo do romaneio. Exibe os três pesos em destaque (bruto,
tara, líquido + valor), tabela de metadados (motorista, veículo, safra, talhão,
cultura, preço/t, destino, notas) e lista de anexos. Ações condicionais por status:
Confirmar (draft→confirmed), Editar (draft), Cancelar (draft ou confirmed).

**O que o usuário faz nesta tela:**
- Confere todos os dados do romaneio
- Confirma, edita ou cancela o romaneio conforme o status
- Visualiza e faz download de anexos

**Funções futuras a implementar:**
- [ ] Exibir a `ledger_entry` vinculada gerada na confirmação (valor lançado, data)
- [ ] Botão "Download PDF" para o romaneio individual
- [ ] Histórico de alterações de status com timestamp e usuário

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | |
| C3 | ✅ | |
| C5 | ✅ | Botão "Cancelar" migrado para padrão Alpine; `x-data` no container de ações |
| C6 | ✅ | |
| C8 | ✅ | Ações condicionais por `can_confirm` / `can_cancel` / `waybill.status` |
| C9 | ✅ | |
| C10 | ✅ | |
| C11 | ✅ | Guards em `driver`, `vehicle`, `harvest`, `field`, `operation_date` |

**Bug corrigido:**
- 🔴 **BUG #4 — C11 — FKs sem guards:** `waybill.driver.name`, `waybill.vehicle.plate`
  e `waybill.harvest.name` eram acessados diretamente. Se qualquer FK estivesse `None`
  (ex: motorista deletado com `SET_NULL`), o template lançaria `AttributeError`.
  **Fix:** `{% if waybill.driver %}...{% else %}—{% endif %}` para o link do motorista;
  `|default:"—"` para `vehicle.plate`, `harvest.name`, `field.name`, `operation_date`.

**Melhoria aplicada:**
- 🟡 **MELHORIA #3 — C5:** Botão "Cancelar" convertido de `onclick="return confirm()"` (JS
  inline) para `type="button" @click="if (confirm('...')) $refs.formCancelar.submit()"` —
  alinhado ao padrão Alpine do roadmap. `x-data` adicionado ao container de ações.

---

### `operations/waybill/_row.html`

**Função:** Partial HTMX para atualização individual de linha na tabela de romaneios.
Renderiza uma `<tr>` com `id="waybill-row-{{ waybill.pk }}"` como alvo de
`hx-swap-oob` ou swap direto após ações (confirmar, cancelar) sem recarregar
a tabela inteira.

**O que o usuário faz nesta tela:** N/A — partial sem interação direta.

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C4 | ✅ | `id` correto para targeting HTMX |
| C6 | ✅ | |
| C11 | ✅ | Guards em `driver` (link) e `vehicle.plate` |

**Bug corrigido:**
- 🔴 **BUG #5 — C11 — FKs sem guards:** `waybill.driver.name` era renderizado
  diretamente dentro de um `<a href="{% url ... pk=waybill.driver.pk %}">`.
  Se `driver` fosse `None`, a tag `{% url %}` lançaria erro antes mesmo do render.
  **Fix:** `{% if waybill.driver %}...<a>...{% else %}—{% endif %}`;
  `waybill.vehicle.plate|default:"—"`.

---

### `operations/waybill/_table.html`

**Função:** Partial HTMX que renderiza a tabela completa de romaneios como alvo de
filtros e paginação (`hx-target="#waybill-table"`). Contém duas versões do conteúdo:
tabela desktop com 9 colunas e cards mobile. Ambas incluem estado vazio.

**O que o usuário faz nesta tela:** N/A — partial; usuário interage via `list.html`.

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | Comentários estruturais válidos |
| C3 | ✅ | |
| C6 | ✅ | |
| C7 | ✅ | `{% empty %}` presente em desktop e mobile |
| C9 | ✅ | `scope="col"` adicionado a todos os `<th>`; `<span class="sr-only">Ações</span>` na coluna de ações |
| C10 | ✅ | |
| C11 | ✅ | Guards em `driver` e `vehicle.plate` em desktop e mobile |

**Bug corrigido:**
- 🔴 **BUG #6 — C11 — FKs sem guards (duplicado em desktop + mobile):** O mesmo
  padrão sem guard do `_row.html` se repetia em ambas as versões da tabela.
  `wb.driver.name` aparecia 2× (tabela e card); `wb.vehicle.plate` aparecia 2×.
  **Fix:** aplicados os mesmos guards do `_row.html` nas duas seções.

**Melhoria aplicada:**
- 🟡 **MELHORIA #4 — C9:** `scope="col"` adicionado a todos os 9 `<th>` da tabela
  desktop; coluna de ações sem cabeçalho visível recebeu `<span class="sr-only">Ações</span>`.

---

## Resumo do Grupo 6 — Romaneios

| Template | Bugs críticos | Melhorias | Status final |
|---|---|---|---|
| `operations/waybill/list.html` | 2 corrigidos | 1 (hx-indicator) | ✅ Corrigido |
| `operations/waybill/form.html` | 1 corrigido | — | ✅ Corrigido |
| `operations/waybill/detail.html` | 1 corrigido | 1 (Alpine cancel) | ✅ Corrigido |
| `operations/waybill/_row.html` | 1 corrigido | — | ✅ Corrigido |
| `operations/waybill/_table.html` | 1 corrigido | 1 (scope=col) | ✅ Corrigido |

**Total Grupo 6: 6 bugs corrigidos · 3 melhorias aplicadas**

---

### Grupo 11 — Fechamentos ✅ Concluído

---

### `finance/settlement/list.html`

**Função:** Listagem de fechamentos em formato de cards verticais (sem filtros/HTMX).
Exibe avatar com inicial do motorista, nome, badge de status, período, contagem de
romaneios e saldo líquido com coloração condicional. Estado vazio com CTA para criar.

**O que o usuário faz nesta tela:**
- Visualiza todos os fechamentos do tenant
- Acessa o detalhe de um fechamento
- Cria um novo fechamento

**Funções futuras a implementar:**
- [ ] Filtro por status e período (HTMX)
- [ ] Filtro por motorista
- [ ] Ordenação por data ou saldo

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks `title`, `nav_title`, `quick_action`, `content` fechados |
| C3 | ✅ | |
| C6 | ✅ | Todos os links via `{% url %}` |
| C7 | ✅ | `{% empty %}` com CTA "Criar primeiro fechamento" |
| C9 | ✅ | `aria-hidden="true"` adicionado ao chevron SVG decorativo |
| C10 | ✅ | |
| C11 | ✅ | Guard `{% if settlement.account %}` adicionado (nome e inicial do avatar) |

**Bug corrigido:**
- 🔴 **BUG #1 — C11 — `settlement.account` sem guard:** `settlement.account.name`
  e `settlement.account.name|first` eram acessados diretamente. Se `account` fosse
  `None` (motorista deletado com `SET_NULL`), o template lançaria `AttributeError`.
  **Fix:** `{% if settlement.account %}...{% else %}?/—{% endif %}` nos dois pontos.

**Melhoria aplicada:**
- 🟡 **MELHORIA #1 — C9:** `aria-hidden="true"` adicionado ao chevron SVG decorativo.

---

### `finance/settlement/form.html`

**Função:** Formulário de criação de fechamento. Seleciona motorista (dropdown) e
período (data início / data fim). Campos simples em HTML raw (não `{{ form.field }}`).
Observação inline explica que romaneios confirmados do período serão incluídos.

**O que o usuário faz nesta tela:**
- Seleciona o motorista e o período para gerar o fechamento
- Corrige erros de validação retornados pelo servidor

**Funções futuras a implementar:**
- [ ] Preview em tempo real dos romaneios que serão incluídos (HTMX ao trocar motorista/período)
- [ ] Suporte a edição de fechamento em rascunho (atualmente só criação)

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks fechados |
| C3 | ✅ | Labels e placeholder em PT-BR |
| C6 | ✅ | Link "Cancelar" via `{% url %}` |
| C8 | ✅ | `non_field_errors` e erros por campo (`driver`, `period_start`, `period_end`) adicionados |
| C9 | ✅ | `<label for="...">` presente em todos os campos |
| C10 | ✅ | |

**Bug corrigido:**
- 🔴 **BUG #2 — C8 — Sem display de erros:** O formulário não exibia
  `form.non_field_errors` nem erros por campo. Envio inválido retornava à tela
  sem qualquer indicação do erro para o usuário.
  **Fix:** bloco `non_field_errors` adicionado acima do form; `{% if form.CAMPO.errors %}`
  adicionado após cada `<input>`/`<select>` (`driver`, `period_start`, `period_end`).

---

### `finance/settlement/detail.html`

**Função:** Detalhe completo do fechamento. Exibe resumo financeiro em 4 KPIs
(produção, descontos, saldo líquido, tonelagem), tabela de romaneios do snapshot,
seção de descontos (combustível + adiantamentos) e metadados de auditoria
(criado/aprovado/fechado em). Ações condicionais por status: Aprovar e Fechar Acerto.

**O que o usuário faz nesta tela:**
- Confere o resumo financeiro do fechamento
- Verifica romaneios e descontos incluídos no snapshot
- Aprova ou fecha definitivamente o acerto conforme o status

**Funções futuras a implementar:**
- [ ] Botão "Download PDF" do fechamento
- [ ] Exibir `ledger_entry` gerada no fechamento
- [ ] Histórico de transições de status com timestamp e usuário

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | Comentários estruturais `{# ── ... ── #}` são documentação válida |
| C2 | ✅ | `extends base.html`; blocks fechados |
| C3 | ✅ | |
| C5 | ✅ | `onclick` inline convertido para padrão Alpine com `x-data` e `$refs` |
| C6 | ✅ | Todos os links via `{% url %}` |
| C9 | ✅ | `scope="col"` adicionado a todos os `<th>` da tabela de romaneios |
| C10 | ✅ | |
| C11 | ✅ | Guard `account.name` no `{% block title %}`; `snapshot_net_balance` guardado com `is not None` antes de comparações |

**Bugs corrigidos:**
- 🔴 **BUG #3 — C11 — `settlement.account.name` sem guard no title:** O `{% block title %}`
  acessava `settlement.account.name` diretamente. Se `account` fosse `None`, o render
  da página inteira falharia antes de exibir qualquer conteúdo.
  **Fix:** `{% if settlement.account %}{{ settlement.account.name }}{% else %}—{% endif %}`.
- 🔴 **BUG #4 — C11 — `snapshot_net_balance` comparado sem guard de `None`:** A
  expressão `{% if settlement.snapshot_net_balance >= 0 %}` era usada 3× para
  definir classes Tailwind de cor. Se `snapshot_net_balance` fosse `None`
  (fechamento recém-criado sem snapshot), Django lançaria `TypeError` ao comparar
  `None >= 0`.
  **Fix:** todas as 3 ocorrências alteradas para
  `{% if settlement.snapshot_net_balance is not None and settlement.snapshot_net_balance >= 0 %}`.
- 🔴 **BUG #5 — C5 — `onclick` inline JS no botão "Fechar Acerto":** Usava
  `onclick="return confirm('...')"` em desacordo com o padrão Alpine adotado no sistema.
  **Fix:** `x-data` adicionado ao container de ações; botão convertido para
  `type="button" @click="if (confirm('...')) $refs.formFechar.submit()"`;
  `x-ref="formFechar"` adicionado ao `<form>` correspondente.

**Melhoria aplicada:**
- 🟡 **MELHORIA #2 — C9:** `scope="col"` adicionado a todos os 5 `<th>` da tabela
  de romaneios do snapshot.

---

## Resumo do Grupo 11 — Fechamentos

| Template | Bugs críticos | Melhorias | Status final |
|---|---|---|---|
| `finance/settlement/list.html` | 1 corrigido | 1 (aria-hidden SVG) | ✅ Corrigido |
| `finance/settlement/form.html` | 1 corrigido | — | ✅ Corrigido |
| `finance/settlement/detail.html` | 3 corrigidos | 1 (scope=col) | ✅ Corrigido |

**Total Grupo 11: 5 bugs corrigidos · 2 melhorias aplicadas**

---

### Grupo 10 — Adiantamentos ✅ Concluído

---

### `finance/advance/list.html`

**Função:** Listagem de adiantamentos em formato de lista vertical (sem HTMX/filtros).
Exibe nome do motorista, badge de status, data, método de pagamento, safra e código
de referência opcionais, valor em destaque vermelho. Botão "Cancelar" inline para
adiantamentos pendentes.

**O que o usuário faz nesta tela:**
- Visualiza todos os adiantamentos do tenant
- Cancela um adiantamento pendente diretamente da lista
- Cria um novo adiantamento

**Funções futuras a implementar:**
- [ ] Filtro por motorista, status e período (HTMX)
- [ ] Totalizador de valores por status na barra de resumo

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks `title`, `nav_title`, `quick_action`, `content` fechados |
| C3 | ✅ | |
| C5 | ✅ | `onclick` inline substituído por padrão Alpine; `x-data` no container |
| C6 | ✅ | Todos os links via `{% url %}` |
| C7 | ✅ | `{% empty %}` com CTA "Registrar adiantamento" |
| C9 | ✅ | `aria-hidden="true"` adicionado ao SVG do `quick_action` |
| C10 | ✅ | |
| C11 | ✅ | Guard `{% if advance.driver %}` adicionado ao nome do motorista |

**Bugs corrigidos:**
- 🔴 **BUG #1 — C11 — `advance.driver.name` sem guard:** O nome do motorista era
  renderizado diretamente. Se `driver` fosse `None` (deletado com `SET_NULL`), o
  template lançaria `AttributeError`.
  **Fix:** `{% if advance.driver %}{{ advance.driver.name }}{% else %}—{% endif %}`.
- 🔴 **BUG #2 — C5 — `onclick` inline JS no botão "Cancelar":** Padrão Alpine não
  aplicado no botão de cancelamento da listagem.
  **Fix:** `x-data` adicionado ao container; botão convertido para
  `type="button" @click="if (confirm('...')) $refs['formCancelar{{ advance.pk }}'].submit()"`;
  `x-ref` dinâmico adicionado ao `<form>`.

**Melhoria aplicada:**
- 🟡 **MELHORIA #1 — C9:** `aria-hidden="true"` adicionado ao SVG do botão "Novo" no `quick_action`.

---

### `finance/advance/form.html`

**Função:** Formulário de criação de adiantamento. Campos: motorista (obrigatório),
safra (opcional), valor, data de pagamento, forma de pagamento, código de comprovante
e observações. Aviso inline que o lançamento é automático ao salvar.

**O que o usuário faz nesta tela:**
- Preenche os dados do adiantamento
- Corrige erros de validação retornados pelo servidor

**Funções futuras a implementar:**
- [ ] Exibir saldo atual do motorista ao selecionar (HTMX `hx-get`)
- [ ] Suporte a edição de adiantamento em rascunho

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks fechados |
| C3 | ✅ | |
| C6 | ✅ | Link "Cancelar" via `{% url %}` |
| C8 | ✅ | `non_field_errors` presente; erros por campo em todos os 7 campos |
| C9 | ✅ | `for="{{ form.CAMPO.id_for_label }}"` adicionado a todos os 7 labels |
| C10 | ✅ | |

**Bug corrigido:**
- 🔴 **BUG #3 — C9 — Todos os `<label>` sem atributo `for`:** Nenhum dos 7 labels
  tinha `for`. Clicar no label não focava o campo; leitores de tela não associavam
  label ao input.
  **Fix:** `for="{{ form.CAMPO.id_for_label }}"` adicionado a todos os 7 labels
  (`driver`, `harvest`, `amount`, `payment_date`, `payment_method`, `reference_code`, `notes`).

**Melhoria aplicada:**
- 🟡 **MELHORIA #2 — C8:** Erros dos 4 campos opcionais (`harvest`, `payment_method`,
  `reference_code`, `notes`) não eram exibidos. Adicionado `{% if form.CAMPO.errors %}`
  para todos.

---

### `finance/advance/detail.html`

**Função:** Detalhe do adiantamento. Exibe valor em destaque vermelho, metadados em
grid (motorista com link, forma de pagamento, safra, comprovante, observações,
ledger entry vinculada). Botão "Cancelar" condicional ao `can_cancel`.

**O que o usuário faz nesta tela:**
- Confere os dados do adiantamento
- Cancela o adiantamento se ainda estiver pendente

**Funções futuras a implementar:**
- [ ] Link para o fechamento no qual o adiantamento foi descontado
- [ ] Histórico de transições de status

**Resultado da auditoria:**

| Critério | Status | Detalhe |
|---|---|---|
| C1 | ✅ | |
| C2 | ✅ | `extends base.html`; blocks fechados |
| C3 | ✅ | |
| C5 | ✅ | `onclick` inline substituído por padrão Alpine; `x-data` + `x-ref` adicionados |
| C6 | ✅ | Todos os links via `{% url %}` |
| C9 | ✅ | |
| C10 | ✅ | |
| C11 | ✅ | Guard `{% if advance.driver %}` adicionado ao `{% block title %}` e ao link/nome no corpo |

**Bugs corrigidos:**
- 🔴 **BUG #4 — C11 — `advance.driver.name` sem guard no `{% block title %}`:**
  Acessava `advance.driver.name` diretamente; render da página inteira falharia se
  `driver` fosse `None`.
  **Fix:** `{% if advance.driver %}{{ advance.driver.name }}{% else %}—{% endif %}`.
- 🔴 **BUG #4 (cont.) — C11 — `advance.driver.pk` no link sem guard:** O `<a href=...>`
  acessava `advance.driver.pk` sem verificar se `driver` existia.
  **Fix:** `{% if advance.driver %}...<a>...{% else %}<span>—</span>{% endif %}`.
- 🔴 **BUG #5 — C5 — `onclick` inline JS no botão "Cancelar":** Usava
  `onclick="return confirm('...')"` em desacordo com o padrão Alpine do sistema.
  **Fix:** `x-data` adicionado ao container de ações; botão convertido para
  `type="button" @click="if (confirm('...')) $refs.formCancelar.submit()"`;
  `x-ref="formCancelar"` adicionado ao `<form>`.

---

## Resumo do Grupo 10 — Adiantamentos

| Template | Bugs críticos | Melhorias | Status final |
|---|---|---|---|
| `finance/advance/list.html` | 2 corrigidos | 1 (aria-hidden SVG) | ✅ Corrigido |
| `finance/advance/form.html` | 1 corrigido | 1 (erros campos opcionais) | ✅ Corrigido |
| `finance/advance/detail.html` | 2 corrigidos | — | ✅ Corrigido |

**Total Grupo 10: 5 bugs corrigidos · 2 melhorias aplicadas**

---

### Grupo 7 — Motoristas ⬜ Pendente

---

## Grupos 1–14

### Grupo 1 — Autenticação e Conta

| Template | Função resumida | Status |
|---|---|---|
| `account/login.html` | Tela de login com email + senha, link "esqueci minha senha" | ⬜ |
| `accounts/profile.html` | Visualização do perfil: nome, avatar, cargo, tenant | ⬜ |
| `accounts/profile_edit.html` | Edição de nome, avatar (com compressão) e senha | ⬜ |

### Grupo 2 — Erros

| Template | Função resumida | Status |
|---|---|---|
| `403.html` | Acesso negado — redireciona para tela anterior ou login | ⬜ |
| `404.html` | Página não encontrada — link para o dashboard | ⬜ |
| `500.html` | Erro interno — orientação ao usuário sem expor detalhes técnicos | ⬜ |

### Grupo 3 — Dashboard

| Template | Função resumida | Status |
|---|---|---|
| `dashboard/index.html` | BI principal: KPIs (romaneios, tonelagem, faturamento, saldo), gráficos ApexCharts, resumo por motorista | ⬜ |
| `dashboard/_quick_search.html` | Partial HTMX: resultados em tempo real da busca da sidebar (motoristas, veículos, romaneios) | ⬜ |

### Grupo 4 — Safras

| Template | Função resumida | Status |
|---|---|---|
| `operations/harvest/list.html` | Lista de safras com cultura, status (ativa/encerrada) e ações | ⬜ |
| `operations/harvest/form.html` | Criar/editar safra: nome, cultura, datas de início/fim, status | ⬜ |
| `operations/harvest/detail.html` | Detalhe da safra: talhões vinculados, romaneios, totais de produção | ⬜ |

### Grupo 5 — Talhões

| Template | Função resumida | Status |
|---|---|---|
| `operations/field/list.html` | Lista de talhões com área (ha) e safra vinculada | ⬜ |
| `operations/field/form.html` | Criar/editar talhão: nome, área, safra | ⬜ |
| `operations/field/detail.html` | Detalhe do talhão com romaneios produzidos | ⬜ |

### Grupo 6 — Romaneios ✅

| Template | Função resumida | Status |
|---|---|---|
| `operations/waybill/list.html` | Lista de romaneios com filtros de status, data, motorista; paginação | ✅ |
| `operations/waybill/form.html` | Criar/editar romaneio: motorista, veículo, talhão, pesos bruto/tara, cultura, preço unitário | ✅ |
| `operations/waybill/detail.html` | Detalhe: pesos, peso líquido, valor calculado, status, ledger entry vinculada, ações (confirmar/cancelar) | ✅ |
| `operations/waybill/_row.html` | Partial HTMX: linha individual da tabela de romaneios (atualizada sem reload) | ✅ |
| `operations/waybill/_table.html` | Partial HTMX: tabela completa de romaneios (target de filtros e paginação) | ✅ |

### Grupo 7 — Motoristas

| Template | Função resumida | Status |
|---|---|---|
| `logistics/driver/list.html` | Lista de motoristas com status CNH, saldo financeiro e ações | ⬜ |
| `logistics/driver/form.html` | Criar/editar motorista: nome, CPF, categoria CNH, validade, status | ⬜ |
| `logistics/driver/detail.html` | Detalhe: dados pessoais, romaneios, adiantamentos, saldo atual, anexos (CNH, foto) | ⬜ |
| `logistics/driver/_table.html` | Partial HTMX: tabela de motoristas (target de busca/filtro) | ⬜ |

### Grupo 8 — Veículos

| Template | Função resumida | Status |
|---|---|---|
| `logistics/vehicle/list.html` | Lista de veículos com placa, tipo, payload e status | ⬜ |
| `logistics/vehicle/form.html` | Criar/editar veículo: placa, tipo, marca, modelo, payload, status | ⬜ |
| `logistics/vehicle/detail.html` | Detalhe: abastecimentos vinculados, romaneios realizados | ⬜ |

### Grupo 9 — Abastecimentos

| Template | Função resumida | Status |
|---|---|---|
| `logistics/fueling/list.html` | Lista de abastecimentos com motorista, veículo, litros e custo total | ⬜ |
| `logistics/fueling/form.html` | Registrar abastecimento: motorista, veículo, data, litros, preço/litro, tipo combustível | ⬜ |
| `logistics/fueling/detail.html` | Detalhe do abastecimento com comprovante (anexo) | ⬜ |

### Grupo 10 — Adiantamentos ✅

| Template | Função resumida | Status |
|---|---|---|
| `finance/advance/list.html` | Lista de adiantamentos por motorista, valor e status (pendente/confirmado/cancelado) | ✅ |
| `finance/advance/form.html` | Criar adiantamento: motorista, valor, método de pagamento, data | ✅ |
| `finance/advance/detail.html` | Detalhe: valor, ledger entry gerada, status, ações (confirmar/cancelar) | ✅ |

### Grupo 11 — Fechamentos ✅

| Template | Função resumida | Status |
|---|---|---|
| `finance/settlement/list.html` | Lista de fechamentos com badge de status, período, contagem de romaneios e saldo líquido | ✅ |
| `finance/settlement/form.html` | Criar fechamento: selecionar motorista e período; romaneios são calculados automaticamente | ✅ |
| `finance/settlement/detail.html` | Detalhe: resumo financeiro (produção, adiantamentos, saldo), ações por status, download PDF | ✅ |

### Grupo 12 — Notificações

| Template | Função resumida | Status |
|---|---|---|
| `notifications/list.html` | Lista completa de notificações do tenant com marcar lidas | ⬜ |
| `notifications/_list.html` | Partial HTMX: lista resumida para o dropdown do header (últimas 10) | ⬜ |

### Grupo 13 — Anexos e Upload

| Template | Função resumida | Status |
|---|---|---|
| `attachments/_list.html` | Partial: galeria de anexos vinculados a qualquer objeto (motorista, romaneio etc.) com download e exclusão | ⬜ |
| `components/upload_zone.html` | Componente de upload com drag & drop, preview e compressão automática (Canvas API) | ⬜ |

### Grupo 14 — Relatórios e PDFs

| Template | Função resumida | Status |
|---|---|---|
| `reports/index.html` | Hub de relatórios disponíveis: links para PDFs individuais e listagens | ⬜ |
| `reports/pdf/waybill.html` | PDF individual de romaneio (WeasyPrint, sem herança de base.html, CSS inline) | ⬜ |
| `reports/pdf/waybill_list.html` | PDF listagem de romaneios por período com totais | ⬜ |
| `reports/pdf/settlement.html` | PDF de fechamento com snapshot de dados imutável | ⬜ |

---

## Ordem de Execução

```
Fase A ✅ — Base + Partials (6 arquivos)          — CONCLUÍDA Sessão 12
Fase B ✅ — Fluxo principal                        — CONCLUÍDA Sessão 13
  operations/waybill/* (5) ✅
  finance/settlement/* (3) ✅
  finance/advance/*    (3) ✅
  logistics/driver/*   (4) ✅
Fase C    — Secundários
  logistics/vehicle/* (3) · logistics/fueling/* (3)
  operations/harvest/* (3) · operations/field/* (3)
Fase D    — Suporte
  dashboard/* (2) · notifications/* (2)
  attachments + upload (2) · reports/* (4)
Fase E    — Auth e Erros
  account/login (1) · accounts/* (2) · 403/404/500 (3)
```

---

## Padrões a Aplicar em Todos os Templates

### Estado vazio (tabelas)
```html
{% empty %}
<tr>
  <td colspan="N" class="px-6 py-10 text-center text-sm text-gray-400">
    Nenhum registro encontrado.
  </td>
</tr>
```

### Badge de status
```html
<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
  {% if obj.status == 'active' %}bg-green-100 text-green-800
  {% elif obj.status == 'inactive' %}bg-gray-100 text-gray-600
  {% else %}bg-yellow-100 text-yellow-800{% endif %}">
  {{ obj.get_status_display }}
</span>
```

### Botão destrutivo com confirmação
```html
<button type="button"
        @click="if (confirm('Confirmar esta ação?')) $refs.formAcao.submit()"
        class="text-red-600 hover:text-red-800 text-sm font-medium">
  Cancelar
</button>
```

### Label acessível obrigatório
```html
<label for="{{ form.campo.id_for_label }}"
       class="block text-sm font-medium text-gray-700 dark:text-gray-300">
  {{ form.campo.label }}
</label>
{{ form.campo }}
{% if form.campo.errors %}
  <p class="mt-1 text-xs text-red-600">{{ form.campo.errors.0 }}</p>
{% endif %}
```

### Guard de FK em template
```html
{# Para FK que gera link: #}
{% if obj.driver %}
<a href="{% url 'logistics:driver-detail' pk=obj.driver.pk %}">{{ obj.driver.name }}</a>
{% else %}—{% endif %}

{# Para FK somente de exibição: #}
{{ obj.vehicle.plate|default:"—" }}
```

---

## Progresso Geral

- Total de templates: **54** (49 originais + 5 novos: Proprietário ×3, Região ×2)
- ✅ Aprovados/Corrigidos: **17** (Fase A: 6 · Fase B Grupo 6: 5 · Fase B Grupo 11: 3 · Fase B Grupo 10: 3)
- 🆕 Novos templates (Sessão 14–15): **5** (logistics/proprietario/: 3 · operations/region/: 2)
- 🔄 Em andamento: **4** (Fase B Grupo 7 — Motoristas)
- ⬜ Pendentes: **28** (templates antigos) + **5** novos = **33** restantes

## Novos Templates (Sessão 14–15)

### logistics/proprietario/ — 3 templates 🆕

| Template | Função |
|---|---|
| `list.html` | Lista proprietários com qtd. de veículos e badges PIX/banco |
| `form.html` | Cadastro/edição com dados pessoais, bancários (banco, ag., conta, tipo) e PIX |
| `detail.html` | Detalhe com dados bancários destacados, lista de veículos vinculados e saldo |

**Critérios C1–C12:** todos aplicados na criação (sem bugs identificados).

### operations/region/ — 2 templates 🆕

| Template | Função |
|---|---|
| `list.html` | Lista regiões com preço/ton e qtd. de talhões vinculados |
| `form.html` | Cadastro/edição com nome, preço padrão e descrição |

**Critérios C1–C12:** todos aplicados na criação.

## Alterações no base.html (Sessão 15) ✅

O `base.html` foi completamente reescrito para ser exclusivo do SafraLog:
- **Removido:** toda a navegação do Sistema RH (employees, payroll, attendance, etc.)
- **Adicionado:** navegação SafraLog completa (Operações, Logística, Financeiro, Relatórios)
- **Corrigido:** HTMX e Alpine.js agora usam bundles locais (`static/js/vendor/htmx.min.js` e `alpine.min.js`) — sem CDN
- **Adicionado:** indicador de safra ativa no sidebar
- **Corrigido:** `{% block quick_action %}` definido uma única vez (sem duplicação)
- **Melhorado:** dark mode toggle, notificações, logout via form POST

---

*Atualizado em: 28/05/2026 — Sessão 14–15: 5 novos templates criados (Proprietário + Região); base.html reescrito como SafraLog-específico com HTMX/Alpine locais; total de templates = 54.*
