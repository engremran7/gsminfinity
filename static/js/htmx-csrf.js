// static/js/htmx-csrf.js
// ============================================================================
// Enterprise-grade CSRF injection for HTMX (Django 5.2+)
// ============================================================================
// Safe, idempotent, CSP-clean, and fully defensive.
// ============================================================================

(function () {
  "use strict";

  // --------------------------------------------------------------------------
  // Prevent double-loading
  // --------------------------------------------------------------------------
  if (window.__HTMX_CSRF_LOADER__) return;
  window.__HTMX_CSRF_LOADER__ = true;

  // --------------------------------------------------------------------------
  // Cookie Parser (hardened)
  // --------------------------------------------------------------------------
  function getCookie(name) {
    try {
      if (!document.cookie) return null;

      const parts = document.cookie.split(";");

      for (let i = 0; i < parts.length; i++) {
        const cookie = parts[i].trim();
        if (cookie.startsWith(name + "=")) {
          return decodeURIComponent(cookie.substring(name.length + 1));
        }
      }
    } catch (err) {
      console.debug("htmx-csrf: cookie parsing failed:", err);
    }
    return null;
  }

  // --------------------------------------------------------------------------
  // Meta Tag Fallback (audit-aware)
  // --------------------------------------------------------------------------
  function getMetaCsrf() {
    try {
      const meta =
        document.querySelector('meta[name="csrf-token"]') ||
        document.querySelector('meta[name="csrfmiddlewaretoken"]') ||
        document.querySelector('meta[name="X-CSRFToken"]');

      return meta ? meta.content : null;
    } catch (err) {
      console.debug("htmx-csrf: meta token read error:", err);
      return null;
    }
  }

  // --------------------------------------------------------------------------
  // Attach CSRF token to HTMX request
  // --------------------------------------------------------------------------
  function onHtmxConfigRequest(evt) {
    try {
      // malformed event → ignore safely
      if (!evt || !evt.detail || !evt.detail.headers) {
        console.debug("htmx-csrf: ignored malformed event");
        return;
      }

      const headers = evt.detail.headers;
      const csrftoken = getCookie("csrftoken") || getMetaCsrf();

      if (!csrftoken) {
        console.warn(
          "htmx-csrf WARNING: No CSRF token available (cookie & meta missing)"
        );
        return;
      }

      // Attach token
      headers["X-CSRFToken"] = csrftoken;

      // Required by secure Django setups
      if (!headers["X-Requested-With"]) {
        headers["X-Requested-With"] = "XMLHttpRequest";
      }

      evt.detail.headers = headers;
    } catch (err) {
      console.debug("htmx-csrf: CSRF attach failed:", err);
    }
  }

  // --------------------------------------------------------------------------
  // Bind listener defensively (HTMX may load late)
  // --------------------------------------------------------------------------
  function safeRegister() {
    try {
      if (!document.body) {
        document.addEventListener("DOMContentLoaded", safeRegister);
        return;
      }

      document.body.addEventListener(
        "htmx:configRequest",
        onHtmxConfigRequest
      );
    } catch (err) {
      console.error("htmx-csrf: listener registration failed:", err);
    }
  }

  safeRegister();
})();
