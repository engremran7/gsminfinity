// static/js/main.js - tiny UI helpers (toasts, AI panel)
// ============================================================================
// Enterprise-grade, CSP-safe, framework-agnostic UI helper script
// (Uses global Bootstrap if available)
// ============================================================================

(function () {
  "use strict";

  // Use non-brand global namespace
  window.AppUI = window.AppUI || {};

  // ---------------------------------------------------------------------------
  // Safe DOM lookup
  // ---------------------------------------------------------------------------
  function safeQuery(id) {
    if (!id || typeof id !== "string") return null;
    try {
      return document.getElementById(id) || null;
    } catch (err) {
      console.warn("main.js: safeQuery failed:", err);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // HTML escape utility (XSS-safe)
  // ---------------------------------------------------------------------------
  function escapeHtml(str) {
    if (typeof str !== "string") return String(str || "");
    return str.replace(/[&<>"'`=\/]/g, function (s) {
      return (
        {
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
          "/": "&#x2F;",
          "`": "&#x60;",
          "=": "&#x3D;",
        }[s] || s
      );
    });
  }

  // ---------------------------------------------------------------------------
  // Bootstrap Toast Wrapper (CSP-safe)
  // ---------------------------------------------------------------------------
  function showToast(message, title = "Info", autohide = true, delay = 4000) {
    const container = safeQuery("app-toasts");
    if (!container) {
      console.warn("main.js: Toast container #app-toasts missing");
      return;
    }

    const id = "t-" + Date.now();

    // Build DOM manually → NO innerHTML injection
    const toastEl = document.createElement("div");
    toastEl.id = id;
    toastEl.className = "toast align-items-center text-bg-white border-0 mb-2";
    toastEl.setAttribute("role", "alert");
    toastEl.setAttribute("aria-live", "assertive");
    toastEl.setAttribute("aria-atomic", "true");

    const flex = document.createElement("div");
    flex.className = "d-flex";

    const body = document.createElement("div");
    body.className = "toast-body";

    body.appendChild(
      document.createTextNode(`${title ? title + ": " : ""}${message}`)
    );

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-close me-2 m-auto";
    btn.setAttribute("data-bs-dismiss", "toast");
    btn.setAttribute("aria-label", "Close");

    flex.appendChild(body);
    flex.appendChild(btn);
    toastEl.appendChild(flex);
    container.appendChild(toastEl);

    try {
      if (window.bootstrap?.Toast) {
        const toast = new window.bootstrap.Toast(toastEl, {
          autohide: !!autohide,
          delay: Number(delay) || 4000,
        });
        toast.show();
      } else {
        // Fallback auto-remove
        setTimeout(() => {
          try {
            toastEl.remove();
          } catch (_) {}
        }, delay);
      }
    } catch (err) {
      console.warn("main.js: Toast error, falling back:", err);
      setTimeout(() => {
        try {
          toastEl.remove();
        } catch (_) {}
      }, delay);
    }
  }

  // ---------------------------------------------------------------------------
  // AI Widget Initialization
  // ---------------------------------------------------------------------------
  let aiInit = false;

  function initAiWidget() {
    if (aiInit) return;
    aiInit = true;

    const aiToggle = safeQuery("ai-toggle");
    const aiPanel = safeQuery("ai-panel");
    const aiClose = safeQuery("ai-close");
    const aiSend = safeQuery("ai-send");
    const aiInput = safeQuery("ai-input");
    const aiMessages = safeQuery("ai-messages");

    // Panel toggle
    if (aiToggle && aiPanel) {
      aiToggle.addEventListener("click", () => {
        try {
          aiPanel.classList.toggle("d-none");
        } catch (err) {
          console.warn("main.js: ai-toggle error:", err);
        }
      });
    }

    if (aiClose && aiPanel) {
      aiClose.addEventListener("click", () => {
        try {
          aiPanel.classList.add("d-none");
        } catch (err) {
          console.warn("main.js: ai-close error:", err);
        }
      });
    }

    // Message appender (private)
    function appendAiMessageInternal(text, who = "bot") {
      if (!aiMessages) return;

      const msg = document.createElement("div");
      msg.textContent = typeof text === "string" ? text : String(text || "");

      msg.className = who === "user"
        ? "small text-end p-2"
        : "small text-muted p-2";

      aiMessages.appendChild(msg);
      aiMessages.scrollTop = aiMessages.scrollHeight;
    }

    AppUI._appendAiMessageInternal = appendAiMessageInternal;

    // CSRF Retrieval
    function getCsrfToken() {
      const meta =
        document.querySelector('meta[name="csrf-token"]') ||
        document.querySelector('meta[name="csrfmiddlewaretoken"]') ||
        document.querySelector('meta[name="csrf"]');
      return meta?.content || null;
    }

    // AI Send handler
    if (aiSend && aiInput && aiMessages) {
      aiSend.addEventListener("click", async () => {
        const q = (aiInput.value || "").trim();
        if (!q) return;

        appendAiMessageInternal(q, "user");
        aiInput.value = "";
        appendAiMessageInternal("Thinking...", "bot");

        try {
          const csrftoken = getCsrfToken();

          const headers = {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
          };
          if (csrftoken) headers["X-CSRFToken"] = csrftoken;

          const response = await fetch("/api/ai/assistant/", {
            method: "POST",
            headers,
            body: JSON.stringify({ question: q }),
            credentials: "same-origin",
          });

          if (!response.ok) {
            appendAiMessageInternal(
              `Assistant unavailable (status ${response.status})`,
              "bot"
            );
            return;
          }

          let data = null;
          try {
            data = await response.json();
          } catch (jsonErr) {
            appendAiMessageInternal(
              "Invalid response received from server.",
              "bot"
            );
            return;
          }

          appendAiMessageInternal(
            data?.answer || data?.result || "No answer available.",
            "bot"
          );
        } catch (err) {
          appendAiMessageInternal(
            "Assistant error: " + (err?.message || String(err)),
            "bot"
          );
        }
      });
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  AppUI.showToast = showToast;

  AppUI.appendAiMessage = function (text, who = "bot") {
    if (!aiInit) initAiWidget();
    if (typeof AppUI._appendAiMessageInternal === "function") {
      AppUI._appendAiMessageInternal(text, who);
    }
  };

  // ---------------------------------------------------------------------------
  // Auto-init on DOM ready
  // ---------------------------------------------------------------------------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAiWidget);
  } else {
    initAiWidget();
  }
})();