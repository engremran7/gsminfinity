// static/js/htmx-csrf.js
// ============================================================================
// Secure CSRF Injection for HTMX (Django 5.2+)
// ============================================================================
//
// Features:
// - Securely attaches Django CSRF token to all HTMX requests
// - Supports cookie token & <meta> token fallback
// - Compatible with HTMX 1.x and 2.x events
// - Adds X-Requested-With header automatically
// - No crashes if HTMX is missing or event is malformed
// - Fully defensive and audit-visible in console
// ============================================================================

(function () {
  "use strict";

  // --------------------------------------------------------------------------
  // Cookie Parser
  // --------------------------------------------------------------------------
  function getCookie(name) {
    try {
      if (!document.cookie) return null;

      const cookies = document.cookie.split(";").map((c) => c.trim());

      for (let i = 0; i < cookies.length; i++) {
        if (cookies[i].startsWith(name + "=")) {
          return decodeURIComponent(cookies[i].substring(name.length + 1));
        }
      }
    } catch (err) {
      console.debug("htmx-csrf: cookie read failed:", err);
    }
    return null;
  }

  // --------------------------------------------------------------------------
  // Meta Tag Fallback
  // --------------------------------------------------------------------------
  function getMetaCsrf() {
    try {
      const meta =
        document.querySelector('meta[name="csrf-token"]') ||
        document.querySelector('meta[name="csrfmiddlewaretoken"]') ||
        document.querySelector('meta[name="X-CSRFToken"]') ||
        null;

      return meta ? meta.content : null;
    } catch (err) {
      console.debug("htmx-csrf: meta token read failed:", err);
      return null;
    }
  }

  // --------------------------------------------------------------------------
  // Attach CSRF token to HTMX request
  // --------------------------------------------------------------------------
  function onHtmxConfigRequest(evt) {
    try {
      if (!evt.detail || !evt.detail.headers) {
        console.debug("htmx-csrf: missing evt.detail.headers");
        return;
      }

      const headers = evt.detail.headers;
      const csrftoken = getCookie("csrftoken") || getMetaCsrf();

      if (!csrftoken) {
        console.warn("htmx-csrf: NO CSRF token found (cookie & meta both missing)");
        return;
      }

      headers["X-CSRFToken"] = csrftoken;

      // Many Django security configs expect this header
      if (!headers["X-Requested-With"]) {
        headers["X-Requested-With"] = "XMLHttpRequest";
      }

      evt.detail.headers = headers;
      // console.debug("htmx-csrf: CSRF attached");
    } catch (err) {
      console.debug("htmx-csrf: failed to attach CSRF header:", err);
    }
  }

  // --------------------------------------------------------------------------
  // Register Listener
  // --------------------------------------------------------------------------
  try {
    document.body.addEventListener("htmx:configRequest", onHtmxConfigRequest);
  } catch (err) {
    console.error("htmx-csrf: unable to register event listener:", err);
  }
})();
