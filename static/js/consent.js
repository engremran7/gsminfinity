/**
 * GSM Infinity - Consent Helpers
 *
 * Provides normalized storage for consent and HTMX integration hooks.
 * Syncs between localStorage, cookies, and the consent banner loader.
 */

window.gsmConsent = {
  STORAGE_KEY: "consent_ads",
  COOKIE_NAME: "consent_status",

  /**
   * Get consent status from localStorage.
   * @returns {boolean} True if consent has been given.
   */
  get() {
    try {
      const v = localStorage.getItem(this.STORAGE_KEY);
      return v === "1" || v === "true";
    } catch (e) {
      return false;
    }
  },

  /**
   * Set consent status in localStorage.
   * @param {boolean|string|number} value - The consent value.
   * @returns {boolean} The normalized value.
   */
  set(value) {
    const normalized = value === true || value === "1" || value === 1;
    try {
      localStorage.setItem(this.STORAGE_KEY, normalized ? "1" : "0");
      // Also remove needs-consent class
      if (normalized && document.body) {
        document.body.classList.remove("needs-consent");
      }
    } catch (e) {}
    return normalized;
  },

  /**
   * Clear consent from localStorage.
   */
  clear() {
    try {
      localStorage.removeItem(this.STORAGE_KEY);
    } catch (e) {}
  },

  /**
   * Check if user has given consent via cookie.
   * @returns {boolean}
   */
  hasGivenConsent() {
    // Check localStorage first (fastest)
    if (this.get()) return true;

    // Check cookie
    try {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const c = cookies[i].trim();
        if (c.startsWith(this.COOKIE_NAME + '=')) {
          const value = decodeURIComponent(c.substring(this.COOKIE_NAME.length + 1));
          if (value === "1" || value === "true") {
            // Sync to localStorage
            this.set(true);
            return true;
          }
          // Try parsing as JSON
          try {
            const parsed = JSON.parse(value);
            if (parsed && typeof parsed === "object") {
              for (const key in parsed) {
                if (Object.prototype.hasOwnProperty.call(parsed, key) && parsed[key]) {
                  // At least one category accepted
                  this.set(true);
                  return true;
                }
              }
            }
          } catch (e) {}
        }
      }
    } catch (e) {}

    return false;
  },

  /**
   * Get consent preferences from cookie as an object.
   * @returns {Object} The consent preferences.
   */
  getPreferences() {
    try {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const c = cookies[i].trim();
        if (c.startsWith(this.COOKIE_NAME + '=') || c.startsWith('consent_prefs=')) {
          const value = decodeURIComponent(c.split('=')[1]);
          try {
            return JSON.parse(value);
          } catch (e) {}
        }
      }
    } catch (e) {
      console.warn('Failed to parse consent cookie:', e);
    }
    return {};
  },

  /**
   * Sync consent status from cookie to localStorage.
   * Call this after page load to ensure consistency.
   */
  syncFromCookie() {
    if (this.hasGivenConsent()) {
      this.set(true);
    }
  }
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

document.addEventListener("removeConsentBanner", function() {
  removeConsentBanner();
  // Sync consent to localStorage when banner is removed
  window.gsmConsent.set(true);
});
document.addEventListener("showToast", showToast);

// Sync consent from cookie to localStorage on page load
document.addEventListener("DOMContentLoaded", function() {
  window.gsmConsent.syncFromCookie();
});

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
