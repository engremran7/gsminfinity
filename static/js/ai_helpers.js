
// AI helper: binds buttons with data-ai-action + data-ai-target, posts to API, and injects responses.
(function () {
  "use strict";
  const d = document;

  function getCSRF() {
    // 1) Prefer centralized CSRF resolver if globally available
    if (window.AppUI && typeof window.AppUI.getCsrfToken === "function") {
      return window.AppUI.getCsrfToken();
    }

    // 2) Fallback via meta tag
    const meta = d.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;

    // 3) Final fallback via cookie
    const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function callAi(action, payload) {
    const endpoint = d.body?.dataset?.aiEndpoint || "/ai/execute/";
    const body = {
      workflow: action || "default",
      input: payload || {},
    };
    const resp = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRF(),
        "X-Requested-With": "XMLHttpRequest",
      },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error("AI request failed");
    const data = await resp.json(); // { ok, run_id, status, output }
    const output = data?.output || {};
    return (
      output.answer ||
      output.result ||
      output.text ||
      output.summary ||
      output
    );
  }

  // AI Workflow API wrapper with safer defaults and strict headers.
  async function runWorkflow(name, payload = {}) {
    if (!name) throw new Error("Missing workflow name");
    try {
      const res = await fetch(`/ai/run/${encodeURIComponent(name)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": getCSRF(),
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
      return await res.json();
    } catch (err) {
      return { ok: false, error: "network-error" };
    }
  }

  function setLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      btn.dataset.originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Thinking...";
    } else {
      btn.disabled = false;
      if (btn.dataset.originalText) btn.textContent = btn.dataset.originalText;
    }
  }

  function applyResult(target, data) {
    if (!target) return;
    const value = data || "";
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
        const currentText =
          (target && ("value" in target ? target.value : target.textContent)) || "";
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
  window.AppUI.runWorkflow = runWorkflow;

  if (d.readyState === "loading") {
    d.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();


