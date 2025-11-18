// static/js/consent.js
// HTMX trigger handlers for consent subsystem.
// - listens for HX triggers sent by server: removeConsentBanner, showToast

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Remove consent banner (server-triggered or HTMX swap)
  // ---------------------------------------------------------------------------
  function onRemoveBanner() {
    try {
      const banner = document.querySelector("#consent-banner");
      if (banner) banner.remove();

      // Remove banner slot if loader created it and it's now empty
      const slot = document.getElementById("consent-banner-slot");
      if (slot && !slot.hasChildNodes()) slot.remove();
    } catch (err) {
      console.debug("consent.js: remove banner failed", err);
    }
  }

  // ---------------------------------------------------------------------------
  // Insert toast HTML returned in payload
  // ---------------------------------------------------------------------------
  function onShowToast(event) {
    try {
      const detail = event && event.detail;
      if (!detail) return;

      const html = detail.html;
      if (!html) return;

      const container =
        document.querySelector("#global-toasts") ||
        document.getElementById("app-toasts");

      if (!container) return;

      container.insertAdjacentHTML("afterbegin", html);
    } catch (err) {
      console.debug("consent.js: showToast failed", err);
    }
  }

  // ---------------------------------------------------------------------------
  // Listen to server-side HTMX dispatched DOM events
  // ---------------------------------------------------------------------------
  document.addEventListener("removeConsentBanner", onRemoveBanner);
  document.addEventListener("showToast", onShowToast);

  // ---------------------------------------------------------------------------
  // Catch HX-Trigger header events sent by Django backend
  // ---------------------------------------------------------------------------
  document.body.addEventListener("htmx:afterOnLoad", function (evt) {
    try {
      const xhr = evt.detail && evt.detail.xhr;
      if (!xhr) return;

      const hxTrigger = xhr.getResponseHeader("HX-Trigger");
      if (!hxTrigger) return;

      let triggers = {};
      try {
        // Strict JSON only — NO eval, NO new Function, NO fallback
        triggers = JSON.parse(hxTrigger);
      } catch (e) {
        console.debug("consent.js: invalid/non-JSON HX-Trigger payload - ignored", e);
        return;
      }

      // Apply triggers
      if (triggers.removeConsentBanner) onRemoveBanner();
      if (triggers.showToast && triggers.showToast.html) {
        onShowToast({ detail: triggers.showToast });
      }
    } catch (err) {
      console.debug("consent.js: htmx after load handler failed", err);
    }
  });

})();
