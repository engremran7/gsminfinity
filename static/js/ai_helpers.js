// AI helper: binds buttons with data-ai-action + data-ai-target, posts to API, and injects responses.
(function () {
  "use strict";
  const d = document;

  function getCSRF() {
    const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    const meta = d.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  async function callAi(action, payload) {
    const endpoint = d.body?.dataset?.aiEndpoint || "/api/ai/ask";
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRF(),
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify({ action, payload }),
    });
    if (!resp.ok) throw new Error("AI request failed");
    return resp.json();
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      btn.dataset.originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Thinking…";
    } else {
      btn.disabled = false;
      if (btn.dataset.originalText) btn.textContent = btn.dataset.originalText;
    }
  }

  function applyResult(target, data) {
    if (!target) return;
    const value = data?.answer || data?.result || "";
    if (target.tagName === "TEXTAREA" || target.tagName === "INPUT") {
      target.value = value;
    } else {
      target.textContent = value;
    }
  }

  function bind() {
    d.querySelectorAll("[data-ai-action]").forEach((btn) => {
      if (btn.dataset.aiBound) return;
      btn.dataset.aiBound = "true";
      btn.addEventListener("click", async (ev) => {
        ev.preventDefault();
        const action = btn.getAttribute("data-ai-action");
        const targetId = btn.getAttribute("data-ai-target");
        const target = targetId ? d.getElementById(targetId) : null;
        const currentText = target && ("value" in target ? target.value : target.textContent) || "";
        setLoading(btn, true);
        try {
          const data = await callAi(action, { text: currentText });
          applyResult(target, data);
          window.AppUI?.showToast?.("AI updated the field", "Success");
        } catch (err) {
          window.AppUI?.showToast?.("AI request failed", "Error");
        } finally {
          setLoading(btn, false);
        }
      });
    });
  }

  window.AppUI = window.AppUI || {};
  window.AppUI.bindAiHelpers = bind;

  if (d.readyState === "loading") {
    d.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
