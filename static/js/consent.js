// Consent helpers and HTMX integration hooks.
// Provides normalized storage for ads consent and removes the banner when instructed.

window.gsmConsent = {
  get() {
    const v = localStorage.getItem("consent_ads");
    return v === "1";
  },
  set(value) {
    const normalized = value === true || value === "1" || value === 1;
    localStorage.setItem("consent_ads", normalized ? "1" : "0");
    return normalized;
  },
};

function removeConsentBanner() {
  try {
    const banner = document.querySelector("#consent-banner");
    if (banner) banner.remove();
    const slot = document.getElementById("consent-banner-slot");
    if (slot && !slot.hasChildNodes()) {
      slot.remove();
    }
  } catch (err) {
    console.debug("consent.js: remove banner failed", err);
  }
}

function showToast(detail) {
  try {
    const payload = detail && detail.detail ? detail.detail : detail;
    if (!payload) return;
    const html = payload.html;
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

document.addEventListener("removeConsentBanner", removeConsentBanner);
document.addEventListener("showToast", showToast);

document.body.addEventListener("htmx:afterOnLoad", function (evt) {
  try {
    const xhr = evt.detail && evt.detail.xhr;
    if (!xhr) return;
    const trigger = xhr.getResponseHeader("HX-Trigger");
    if (!trigger) return;
    let data = {};
    try {
      data = JSON.parse(trigger);
    } catch (err) {
      console.debug(
        "consent.js: invalid/non-JSON HX-Trigger payload - ignored",
        err
      );
      return;
    }
    if (data.removeConsentBanner) removeConsentBanner();
    if (data.showToast && data.showToast.html) showToast({ detail: data.showToast });
  } catch (err) {
    console.debug("consent.js: htmx after load handler failed", err);
  }
});
