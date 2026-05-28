/**
 * SafraLog — main.js
 * Configuração global: HTMX, Alpine.js, utilidades de UI.
 * Carregado após Alpine e HTMX via defer no base.html.
 */

// ============================================================
// HTMX — Configuração global
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  // CSRF token automático em todas as requisições HTMX
  document.body.addEventListener("htmx:configRequest", (event) => {
    const csrf = document.querySelector("meta[name='csrf-token']")?.content
      || document.querySelector("[name='csrfmiddlewaretoken']")?.value;
    if (csrf) {
      event.detail.headers["X-CSRFToken"] = csrf;
    }
  });

  // Loading bar no topo da página
  const loadingBar = document.getElementById("htmx-loading-bar");
  if (loadingBar) {
    document.body.addEventListener("htmx:beforeRequest", () => {
      loadingBar.classList.add("htmx-request");
    });
    document.body.addEventListener("htmx:afterRequest", () => {
      setTimeout(() => loadingBar.classList.remove("htmx-request"), 300);
    });
  }

  // Scroll to top em trocas de página inteira
  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target === document.body) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });

  // Fechar modal em resposta HTMX com header HX-Trigger: closeModal
  document.body.addEventListener("closeModal", () => {
    const overlay = document.getElementById("modal-overlay");
    if (overlay) {
      overlay.dispatchEvent(new CustomEvent("close-modal"));
    }
  });

  // Mostrar toast via header HX-Trigger: showMessage
  document.body.addEventListener("showMessage", (event) => {
    const { message, type } = event.detail || {};
    if (message) showToast(message, type || "info");
  });

  // Erros HTMX
  document.body.addEventListener("htmx:responseError", (event) => {
    const status = event.detail.xhr?.status;
    if (status === 403) {
      showToast("Acesso negado. Faça login novamente.", "error");
    } else if (status === 404) {
      showToast("Recurso não encontrado.", "error");
    } else if (status >= 500) {
      showToast("Erro interno do servidor. Tente novamente.", "error");
    }
  });
});

// ============================================================
// Toast global
// ============================================================
window.showToast = function (message, type = "info") {
  document.dispatchEvent(new CustomEvent("show-toast", {
    detail: { message, type }
  }));
};

// ============================================================
// Alpine.js — Componentes globais
// ============================================================
document.addEventListener("alpine:init", () => {

  // Dropdown genérico
  Alpine.data("dropdown", (initialOpen = false) => ({
    open: initialOpen,
    toggle() { this.open = !this.open; },
    close() { this.open = false; },
  }));

  // Confirmação de ação perigosa
  Alpine.data("confirmAction", ({ message = "Tem certeza?", onConfirm = null } = {}) => ({
    pending: false,
    async confirm() {
      if (!window.confirm(message)) return;
      this.pending = true;
      try {
        if (typeof onConfirm === "function") await onConfirm();
      } finally {
        this.pending = false;
      }
    },
  }));

  // Tabs
  Alpine.data("tabs", (defaultTab = 0) => ({
    active: defaultTab,
    setTab(tab) { this.active = tab; },
    isActive(tab) { return this.active === tab; },
  }));

  // Modal global (recebe conteúdo via HTMX)
  Alpine.data("globalModal", () => ({
    open: false,
    loading: false,
    openModal() { this.open = true; document.body.classList.add("overflow-hidden"); },
    closeModal() { this.open = false; document.body.classList.remove("overflow-hidden"); },
    init() {
      // Ouve eventos HTMX para abrir modal
      document.body.addEventListener("htmx:afterSwap", (e) => {
        if (e.detail.target.id === "modal-content") {
          this.openModal();
        }
      });
      // Fecha via Alpine event
      this.$el.addEventListener("close-modal", () => this.closeModal());
      // Fecha com ESC
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && this.open) this.closeModal();
      });
    },
  }));

  // Copiador de texto (ex: chave de API, número de romaneio)
  Alpine.data("copyText", (text) => ({
    copied: false,
    async copy() {
      try {
        await navigator.clipboard.writeText(text);
        this.copied = true;
        setTimeout(() => { this.copied = false; }, 2000);
      } catch {
        showToast("Não foi possível copiar.", "error");
      }
    },
  }));

  // Contador de caracteres em textarea
  Alpine.data("charCounter", (max = 500) => ({
    count: 0,
    max,
    update(el) { this.count = el.value.length; },
    get remaining() { return this.max - this.count; },
    get isOver() { return this.count > this.max; },
  }));

});

// ============================================================
// Utilitários DOM globais
// ============================================================

// Formata números BR
window.formatCurrency = (value) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value);

window.formatNumber = (value, decimals = 2) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: decimals }).format(value);

// Throttle simples
window.throttle = (fn, delay) => {
  let last = 0;
  return (...args) => {
    const now = Date.now();
    if (now - last >= delay) { last = now; fn(...args); }
  };
};

// ============================================================
// Service Worker (opcional — preparado para PWA futura)
// ============================================================
if ("serviceWorker" in navigator && window.location.protocol === "https:") {
  // Registrar SW quando existir
  // navigator.serviceWorker.register("/sw.js").catch(() => {});
}
