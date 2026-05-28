/**
 * SafraLog — upload.js
 * Alpine.js component para upload de arquivos.
 * Suporta: drag-and-drop, Ctrl+V (clipboard), câmera mobile, seleção.
 * Upload assíncrono via XHR — sem reload de página.
 *
 * COMPRESSÃO CLIENT-SIDE (Canvas API):
 * Imagens são comprimidas antes do upload — crítico para internet rural.
 * Reduz uploads de 3-8 MB para ~200-400 KB sem perda visual perceptível.
 * PDFs e documentos são enviados sem alteração.
 */

// ============================================================
// COMPRESSÃO DE IMAGEM — Canvas API
// ============================================================

/**
 * Comprime uma imagem usando Canvas API.
 * Redimensiona se necessário e converte para JPEG com qualidade controlada.
 *
 * @param {File} file - Arquivo de imagem original
 * @param {Object} options
 * @param {number} options.maxWidth  - Largura máxima em px (default: 1920)
 * @param {number} options.maxHeight - Altura máxima em px (default: 1080)
 * @param {number} options.quality   - Qualidade JPEG 0-1 (default: 0.82)
 * @param {number} options.maxSizeKB - Tamanho máximo alvo em KB (default: 600)
 * @returns {Promise<File>} Arquivo comprimido (ou original se não for imagem)
 */
async function compressImage(file, options = {}) {
  const {
    maxWidth  = 1920,
    maxHeight = 1080,
    quality   = 0.82,
    maxSizeKB = 600,
  } = options;

  // Só comprime imagens — PDFs e docs passam direto
  if (!file.type.startsWith("image/")) return file;

  // GIFs animados: não comprime (canvas perde a animação)
  if (file.type === "image/gif") return file;

  // Se já está abaixo do limite, não comprime
  if (file.size <= maxSizeKB * 1024) return file;

  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(url);

      // Calcula dimensões respeitando aspect ratio
      let { width, height } = img;
      if (width > maxWidth || height > maxHeight) {
        const ratio = Math.min(maxWidth / width, maxHeight / height);
        width  = Math.round(width  * ratio);
        height = Math.round(height * ratio);
      }

      const canvas = document.createElement("canvas");
      canvas.width  = width;
      canvas.height = height;

      const ctx = canvas.getContext("2d");
      // Fundo branco para imagens com transparência (PNG→JPEG)
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);

      // Tenta comprimir com qualidade decrescente até atingir maxSizeKB
      let currentQuality = quality;
      const tryCompress = () => {
        canvas.toBlob(
          (blob) => {
            if (!blob) { resolve(file); return; }

            // Se ainda está grande e qualidade pode baixar mais, tenta de novo
            if (blob.size > maxSizeKB * 1024 && currentQuality > 0.4) {
              currentQuality -= 0.1;
              tryCompress();
              return;
            }

            // Usa o resultado só se for menor que o original
            if (blob.size >= file.size) { resolve(file); return; }

            const outputName = file.name.replace(/\.[^.]+$/, "") + ".jpg";
            const compressed = new File([blob], outputName, {
              type: "image/jpeg",
              lastModified: Date.now(),
            });
            resolve(compressed);
          },
          "image/jpeg",
          currentQuality
        );
      };

      tryCompress();
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(file); // Fallback: original sem compressão
    };

    img.src = url;
  });
}

// ============================================================
// ALPINE COMPONENT
// ============================================================

document.addEventListener("alpine:init", () => {
  Alpine.data("uploadZone", ({ objectType, objectId, uploadUrl }) => ({
    // Estado
    dragover: false,
    files: [], // { name, size, originalSize, preview, progress, status, attachmentId, error }

    // ========================================================
    // HANDLERS
    // ========================================================

    handleDrop(event) {
      this.dragover = false;
      this.processFiles(Array.from(event.dataTransfer.files));
    },

    handlePaste(event) {
      const active = document.activeElement;
      const isInput = ["INPUT", "TEXTAREA", "SELECT"].includes(active?.tagName);
      if (isInput && active.type !== "file") return;

      const items = Array.from(event.clipboardData?.items || []);
      const imageItems = items.filter(item => item.type.startsWith("image/"));
      if (imageItems.length === 0) return;

      event.preventDefault();
      const files = imageItems.map(item => item.getAsFile()).filter(Boolean);
      this.processFiles(files);
    },

    handleFileSelect(event) {
      this.processFiles(Array.from(event.target.files));
      event.target.value = ""; // Reset para permitir re-seleção
    },

    // ========================================================
    // PROCESSAMENTO + COMPRESSÃO
    // ========================================================

    async processFiles(rawFiles) {
      for (const raw of rawFiles) {
        if (!this.validateFile(raw)) continue;

        const originalSize = raw.size;
        const fileEntry = {
          name: raw.name || `imagem_${Date.now()}.jpg`,
          size: originalSize,
          originalSize,
          preview: null,
          progress: 0,
          status: "compressing", // compressing | uploading | done | error
          attachmentId: null,
          error: null,
          compressed: false,
        };

        // Preview imediato a partir do original (antes da compressão)
        if (raw.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = (e) => { fileEntry.preview = e.target.result; };
          reader.readAsDataURL(raw);
        }

        this.files.push(fileEntry);
        const index = this.files.length - 1;

        // Comprime antes de enviar
        let file = raw;
        if (raw.type.startsWith("image/")) {
          try {
            file = await compressImage(raw, {
              maxWidth:  1920,
              maxHeight: 1080,
              quality:   0.82,
              maxSizeKB: 600,
            });

            if (file !== raw) {
              this.files[index].size       = file.size;
              this.files[index].name       = file.name;
              this.files[index].compressed = true;
            }
          } catch (err) {
            console.warn("Compressão falhou, enviando original:", err);
            file = raw;
          }
        }

        this.uploadFile(file, index);
      }
    },

    validateFile(file) {
      const maxSize = 50 * 1024 * 1024; // 50 MB
      const allowed = [
        "image/jpeg", "image/png", "image/webp", "image/gif",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain", "text/csv",
      ];

      if (file.size > maxSize) {
        this.showToast(`"${file.name}" é muito grande (máx. 50MB)`, "error");
        return false;
      }
      if (!allowed.includes(file.type) && !file.type.startsWith("image/")) {
        this.showToast(`Tipo não suportado: ${file.type}`, "error");
        return false;
      }
      return true;
    },

    async uploadFile(file, index) {
      this.files[index].status = "uploading";

      const formData = new FormData();
      formData.append("file", file, this.files[index].name);
      formData.append("object_type", objectType);
      formData.append("object_id", objectId);

      try {
        const csrf =
          document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
          document.querySelector("meta[name=csrf-token]")?.content;

        const xhr = new XMLHttpRequest();
        xhr.open("POST", uploadUrl);
        xhr.setRequestHeader("X-CSRFToken", csrf);
        xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) {
            this.files[index].progress = Math.round((e.loaded / e.total) * 100);
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const data = JSON.parse(xhr.responseText);
              this.files[index].status   = "done";
              this.files[index].progress = 100;
              this.files[index].attachmentId = data.id;

              const savedKB = Math.round(
                (this.files[index].originalSize - this.files[index].size) / 1024
              );
              const msg = this.files[index].compressed && savedKB > 10
                ? `Enviado! Comprimido ${savedKB} KB`
                : "Arquivo enviado!";
              this.showToast(msg, "success");

              document.dispatchEvent(new CustomEvent("attachment-uploaded", {
                detail: { attachment: data, objectType, objectId },
              }));
            } catch {
              this.files[index].status = "error";
              this.showToast("Erro ao processar resposta do servidor.", "error");
            }
          } else {
            this.files[index].status = "error";
            this.showToast(`Erro ao enviar: HTTP ${xhr.status}`, "error");
          }
        };

        xhr.onerror = () => {
          this.files[index].status = "error";
          this.showToast("Falha de conexão. Verifique o sinal.", "error");
        };

        xhr.send(formData);
      } catch (err) {
        this.files[index].status = "error";
        console.error("Upload error:", err);
        this.showToast("Erro inesperado no upload.", "error");
      }
    },

    removeFile(index) {
      this.files.splice(index, 1);
    },

    // ========================================================
    // UTILIDADES
    // ========================================================

    formatSize(bytes) {
      if (bytes < 1024)           return `${bytes} B`;
      if (bytes < 1024 * 1024)    return `${(bytes / 1024).toFixed(1)} KB`;
      return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    },

    compressionRatio(entry) {
      if (!entry.compressed || entry.originalSize === entry.size) return null;
      const pct = Math.round((1 - entry.size / entry.originalSize) * 100);
      return pct > 5 ? `−${pct}%` : null;
    },

    showToast(message, type = "info") {
      document.dispatchEvent(new CustomEvent("show-toast", { detail: { message, type } }));
    },
  }));
});

// ============================================================
// TOAST — global, independente do Alpine
// ============================================================

document.addEventListener("show-toast", (event) => {
  const { message, type = "info" } = event.detail;
  const container = document.getElementById("toast-container");
  if (!container) return;

  const colors = {
    success: "bg-green-600 text-white",
    error:   "bg-red-600 text-white",
    info:    "bg-gray-900 dark:bg-gray-800 text-white",
    warning: "bg-yellow-500 text-white",
  };

  const toast = document.createElement("div");
  toast.className = [
    "pointer-events-auto flex items-center gap-2.5 px-4 py-2.5",
    "rounded-xl shadow-lg text-sm",
    colors[type] || colors.info,
    "transform translate-y-2 opacity-0 transition-all duration-200",
  ].join(" ");
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      toast.classList.remove("translate-y-2", "opacity-0");
    });
  });

  setTimeout(() => {
    toast.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => toast.remove(), 200);
  }, 3500);
});

// ============================================================
// HTMX: refresh lista de anexos após upload
// ============================================================

document.addEventListener("attachment-uploaded", () => {
  const list = document.querySelector("[data-attachments-list]");
  if (list) htmx.trigger(list, "refresh");
});
