// static/js/consent.js
// HTMX trigger handlers for consent subsystem.
// - listens for HX triggers sent by server: removeConsentBanner, showToast
(function () {
  "use strict";

  // Remove banner when server sends event (or when HTMX swaps an empty fragment)
  function onRemoveBanner() {
    try {
      const banner = document.querySelector("#cookie-banner");
      if (banner) banner.remove();
    } catch (err) {
      console.debug("consent.js: remove banner failed", err);
    }
  }

  // Insert toast HTML returned in payload
  function onShowToast(event) {
    try {
      const detail = event && event.detail;
      // HTMX may trigger native CustomEvent with .detail containing the payload,
      // but our hx_response places JSON in HX-Trigger header which HTMX converts
      // into a DOM event; htmx dispatches an event named same as trigger.
      // The following handles both spec variants:
      const payload = detail || {};
      const html = payload.html || (detail && detail.html) || (event && event.detail && event.detail.html);
      if (!html) return;

      const container = document.querySelector("#global-toasts") || document.getElementById("app-toasts");
      if (!container) return;

      // Insert HTML as first child
      container.insertAdjacentHTML("afterbegin", html);
    } catch (err) {
      console.debug("consent.js: showToast failed", err);
    }
  }

  // HTMX emits DOM events with names matching the trigger keys,
  // but to be robust we also listen for a generic custom event payload.
  document.addEventListener("removeConsentBanner", onRemoveBanner);
  document.addEventListener("showToast", onShowToast);

  // Also watch for htmx:afterOnLoad to catch HX-Trigger header scenarios
  document.body.addEventListener("htmx:afterOnLoad", function (evt) {
    try {
      const hxTrigger = evt.detail && evt.detail.xhr && evt.detail.xhr.getResponseHeader && evt.detail.xhr.getResponseHeader("HX-Trigger");
      if (!hxTrigger) return;
      let triggers = {};
      try {
        triggers = JSON.parse(hxTrigger);
      } catch (e) {
        // hxTrigger might already be a stringified object without quotes; attempt eval-like parse guardedly
        try {
          triggers = (new Function("return " + hxTrigger))();
        } catch (e2) {
          console.debug("consent.js: invalid HX-Trigger payload", e2);
          return;
        }
      }
      if (triggers.removeConsentBanner) onRemoveBanner();
      if (triggers.showToast && triggers.showToast.html) onShowToast({ detail: triggers.showToast });
    } catch (err) {
      console.debug("consent.js: htmx after load handler failed", err);
    }
  });

})();
