// static/js/main.js - tiny UI helpers (toasts, AI panel)
// =============================================================================
// GSMInfinity UI Support Script
// Enterprise-grade, defensive, CSP-compatible, Django-safe
// =============================================================================
//
// Zero dependencies except Bootstrap Bundle (already globally available).
// Provides:
//   - Safe bootstrap toasts
//   - AI Chat Panel widget
//   - CSRF-aware AJAX calls
//   - Hardened DOM operations
//
// All functionality is preserved, improved, and made airtight without shrinking.
// =============================================================================

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Safe DOM lookup
  // ---------------------------------------------------------------------------
  function safeQuery(id) {
    try {
      return document.getElementById(id);
    } catch (err) {
      console.debug("main.js: safeQuery failed:", err);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // HTML escape utility
  // ---------------------------------------------------------------------------
  function escapeHtml(str) {
    if (typeof str !== "string") return String(str);
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
  // Bootstrap Toast Wrapper
  // ---------------------------------------------------------------------------
  function showToast(message, title = "Info", autohide = true, delay = 4000) {
    const container = safeQuery("app-toasts");
    if (!container) {
      console.warn("main.js: Toast container #app-toasts missing");
      return;
    }

    const id = "t-" + Date.now();
    const wrapper = document.createElement("div");

    wrapper.innerHTML = `
      <div id="${id}"
        class="toast align-items-center text-bg-white border-0 mb-2"
        role="alert" aria-live="assertive" aria-atomic="true">

        <div class="d-flex">
          <div class="toast-body">
            <strong>${escapeHtml(title)}:</strong> ${escapeHtml(message)}
          </div>
          <button type="button" class="btn-close me-2 m-auto"
                  data-bs-dismiss="toast"
                  aria-label="Close"></button>
        </div>
      </div>
    `;

    const el = wrapper.firstElementChild;
    if (!el) return;

    container.appendChild(el);

    // Safe bootstrap handling
    try {
      if (window.bootstrap && typeof window.bootstrap.Toast === "function") {
        const toast = new window.bootstrap.Toast(el, {
          autohide: !!autohide,
          delay: Number(delay) || 4000,
        });
        toast.show();
      } else {
        // Fallback simple fade-out removal
        setTimeout(() => {
          try {
            el.remove();
          } catch (e) {}
        }, delay || 4000);
      }
    } catch (err) {
      console.debug("main.js: Toast fallback triggered:", err);
      setTimeout(() => {
        try {
          el.remove();
        } catch (e) {}
      }, delay || 4000);
    }
  }

  // ---------------------------------------------------------------------------
  // AI Widget Initialization
  // ---------------------------------------------------------------------------
  let aiInitialized = false;

  function initAiWidget() {
    if (aiInitialized) return;
    aiInitialized = true;

    const aiToggle = safeQuery("ai-toggle");
    const aiPanel = safeQuery("ai-panel");
    const aiClose = safeQuery("ai-close");
    const aiSend = safeQuery("ai-send");
    const aiInput = safeQuery("ai-input");
    const aiMessages = safeQuery("ai-messages");

    // Safe toggle
    if (aiToggle && aiPanel) {
      aiToggle.addEventListener("click", () => {
        aiPanel.classList.toggle("d-none");
      });

      if (aiClose) {
        aiClose.addEventListener("click", () => {
          aiPanel.classList.add("d-none");
        });
      }
    }

    // Append message
    function appendAiMessage(text, who = "bot") {
      if (!aiMessages) return;
      const msg = document.createElement("div");
      msg.className = who === "bot" ? "small text-muted p-2" : "small text-end p-2";
      msg.textContent = text;
      aiMessages.appendChild(msg);
      aiMessages.scrollTop = aiMessages.scrollHeight;
    }

    // Send logic
    if (aiSend && aiInput && aiMessages) {
      aiSend.addEventListener("click", async () => {
        const q = (aiInput.value || "").trim();
        if (!q) return;

        appendAiMessage(q, "user");
        aiInput.value = "";
        appendAiMessage("Thinking...", "bot");

        try {
          const metaToken =
            document.querySelector('meta[name="csrf-token"]') ||
            document.querySelector('meta[name="csrfmiddlewaretoken"]');

          const csrftoken = metaToken ? metaToken.content : null;

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
            appendAiMessage(
              `Assistant unavailable (status ${response.status})`,
              "bot"
            );
            return;
          }

          const data = await response.json();
          appendAiMessage(data.answer || data.result || "No answer available", "bot");
        } catch (err) {
          appendAiMessage("Assistant error: " + (err?.message || err), "bot");
        }
      });
    }

    // Expose internal function safely
    window.GSMInfinity.appendAiMessageInternal = appendAiMessage;
  }

  // ---------------------------------------------------------------------------
  // Public API Exposure
  // ---------------------------------------------------------------------------
  window.GSMInfinity = window.GSMInfinity || {};

  window.GSMInfinity.showToast = showToast;

  // FIXED: Avoid infinite recursion from your original buggy version
  window.GSMInfinity.appendAiMessage = function (text, who = "bot") {
    if (!aiInitialized) initAiWidget();
    if (window.GSMInfinity.appendAiMessageInternal) {
      window.GSMInfinity.appendAiMessageInternal(text, who);
    }
  };

  // ---------------------------------------------------------------------------
  // DOM Ready Auto-Init
  // ---------------------------------------------------------------------------
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAiWidget);
  } else {
    initAiWidget();
  }
})();
