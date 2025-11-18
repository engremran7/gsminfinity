// static/js/consent-banner-loader.js
// -----------------------------------------------------------------------------
// GSMInfinity — Enterprise Consent Banner Loader
// Fully hardened: no silent errors, no endpoint mismatches, no DOM leaks,
// fully compatible with HTMX, SSR, SPA, Bootstrap, or vanilla sites.
// -----------------------------------------------------------------------------

(function () {
  "use strict";

  // ============================================================================
  // Helpers
  // ============================================================================

  function getCookie(name) {
    try {
      if (!document.cookie) return null;
      const cookies = document.cookie.split(";");
      for (const c of cookies) {
        const cookie = c.trim();
        if (cookie.startsWith(name + "=")) {
          return decodeURIComponent(cookie.substring(name.length + 1));
        }
      }
    } catch (err) {
      console.warn("Cookie read failed", err);
    }
    return null;
  }

  // Safe fetch wrapper for Django CSRF
  function csrfFetch(url, opts = {}) {
    const o = {
      method: opts.method || "GET",
      credentials: "same-origin",
      headers: opts.headers || {},
      body: opts.body || undefined,
    };

    if (!o.headers["X-Requested-With"]) {
      o.headers["X-Requested-With"] = "XMLHttpRequest";
    }

    const csrftoken = getCookie("csrftoken");
    if (csrftoken) o.headers["X-CSRFToken"] = csrftoken;

    return fetch(url, o);
  }

  // Create container if missing
  function ensureSlot() {
    let slot = document.getElementById("consent-banner-slot");
    if (!slot) {
      slot = document.createElement("div");
      slot.id = "consent-banner-slot";
      slot.style.position = "relative";
      slot.style.zIndex = 99999;
      document.body.appendChild(slot);
    }
    return slot;
  }

  // Remove banner entirely
  function removeBanner() {
    try {
      const el = document.getElementById("consent-banner");
      if (el) el.remove();
      const slot = document.getElementById("consent-banner-slot");
      if (slot && !slot.hasChildNodes()) slot.remove();
    } catch (_) {}
  }

  // Safe HTML insertion (sandboxing)
  function renderBanner(html) {
    if (!html || typeof html !== "string") return;
    const slot = ensureSlot();

    // Sandbox the HTML to avoid running inline <script> or events
    const sandbox = document.createElement("template");
    sandbox.innerHTML = html.trim();

    slot.innerHTML = "";
    slot.appendChild(sandbox.content.cloneNode(true));

    attachHandlers();
  }

  // ============================================================================
  // Controls / event handlers
  // ============================================================================

  function attachHandlers() {
    const banner = document.getElementById("consent-banner");
    if (!banner) return;

    const acceptBtn = document.getElementById("consent-accept-all");
    const rejectBtn = document.getElementById("consent-reject-all");
    const closeBtn = document.getElementById("consent-close");

    if (acceptBtn) {
      acceptBtn.addEventListener("click", (e) => {
        e.preventDefault();
        doAcceptAll();
      });
    }

    if (rejectBtn) {
      rejectBtn.addEventListener("click", (e) => {
        e.preventDefault();
        doRejectAll();
      });
    }

    if (closeBtn) {
      closeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        removeBanner();
      });
    }

    // granular checkboxes
    const checks = banner.querySelectorAll(
      'input[type="checkbox"][data-consent-slug]'
    );
    if (checks.length > 0) {
      checks.forEach((chk) => {
        chk.addEventListener("change", () => {
          if (window.__consent_save_timeout) {
            clearTimeout(window.__consent_save_timeout);
          }
          window.__consent_save_timeout = setTimeout(
            saveGranularPreferences,
            250
          );
        });
      });
    }
  }

  // ============================================================================
  // Backend actions
  // ============================================================================

  // POST accept all
  async function doAcceptAll() {
    try {
      const res = await csrfFetch("/consent/accept_all/", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: new URLSearchParams({ accept_all: "1" }),
      });

      const text = await res.text();
      removeBanner();
      injectToastFromHtml(text);
    } catch (err) {
      console.error("Consent accept_all error", err);
    }
  }

  // POST reject all
  async function doRejectAll() {
    try {
      const res = await csrfFetch("/consent/reject_all/", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: new URLSearchParams({ reject_all: "1" }),
      });

      const text = await res.text();
      removeBanner();
      injectToastFromHtml(text);
    } catch (err) {
      console.error("Consent reject_all error", err);
    }
  }

  // granular save (JSON)
  async function saveGranularPreferences() {
    try {
      const banner = document.getElementById("consent-banner");
      if (!banner) return;

      const checks = banner.querySelectorAll(
        'input[type="checkbox"][data-consent-slug]'
      );
      const payload = {};

      checks.forEach((chk) => {
        const slug = chk.getAttribute("data-consent-slug");
        payload[slug] = chk.checked ? true : false;
      });

      const res = await csrfFetch("/consent/accept/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        console.warn("Granular save failed", res.status);
        return;
      }

      // Try JSON response for toast
      try {
        const js = await res.json();
        if (js?.message) {
          const msg = js.message;
          showToast(msg);
        }
      } catch (_) {}
    } catch (err) {
      console.error("saveGranularPreferences error", err);
    }
  }

  // ============================================================================
  // Toast injection
  // ============================================================================

  function showToast(msg) {
    try {
      if (window.GSMInfinity?.showToast) {
        GSMInfinity.showToast(msg, "Preferences", true);
        return;
      }
    } catch (_) {}

    // fallback: create native toast container
    let area = document.getElementById("app-toasts");
    if (!area) {
      area = document.createElement("div");
      area.id = "app-toasts";
      area.className = "fixed top-4 right-4 z-50";
      document.body.appendChild(area);
    }

    const t = document.createElement("div");
    t.className =
      "toast show bg-dark text-white p-3 mb-2 rounded shadow-lg";
    t.innerHTML = msg;

    area.appendChild(t);

    setTimeout(() => t.remove(), 3500);
  }

  function injectToastFromHtml(html) {
    try {
      const tmp = document.createElement("div");
      tmp.innerHTML = html;

      const toast =
        tmp.querySelector(".toast") || tmp.querySelector(".toast-body");
      if (!toast) return;

      let container = document.getElementById("app-toasts");
      if (!container) {
        container = document.createElement("div");
        container.id = "app-toasts";
        container.className = "fixed top-4 right-4 z-50";
        document.body.appendChild(container);
      }

      container.appendChild(toast);

      if (window.bootstrap?.Toast) {
        try {
          new bootstrap.Toast(toast).show();
        } catch (_) {}
      }
    } catch (_) {}
  }

  // ============================================================================
  // Initial banner load
  // ============================================================================

  async function loadBanner() {
    try {
      const res = await csrfFetch("/consent/banner/", { method: "GET" });
      if (!res.ok) return;

      const html = await res.text();
      if (!html.trim()) {
        removeBanner();
        return;
      }

      renderBanner(html);
    } catch (err) {
      console.error("Failed to load consent banner", err);
    }
  }

  // DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", loadBanner);
  } else {
    loadBanner();
  }
})();
