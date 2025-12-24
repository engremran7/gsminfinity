/**
 * GSM Infinity Consent Banner Loader
 *
 * Handles cookie consent banner display and preference storage.
 * Syncs with both cookies and localStorage for reliable consent detection.
 */
(function() {
  "use strict";

  // Prevent double-loading
  if (typeof window !== "undefined" && window.__CONSENT_BANNER_LOADER_LOADED__) return;
  if (typeof window !== "undefined") window.__CONSENT_BANNER_LOADER_LOADED__ = true;

  window.AppConsent = window.AppConsent || {};

  // Default configuration
  var defaults = {
    cookieName: "consent_status",
    localStorageKey: "consent_ads",
    endpoints: {
      banner: "/consent/banner/",
      acceptAll: "/consent/accept_all/",
      rejectAll: "/consent/reject_all/",
      accept: "/consent/accept/"
    },
    bannerSlotId: "consent-banner-slot",
    bannerId: "consent-banner",
    toastsId: "app-toasts",
    autoLoad: true
  };

  // Merge with window.CONSENT_CONFIG if available
  var config = (function() {
    try {
      if (typeof window !== "undefined" && window.CONSENT_CONFIG && typeof window.CONSENT_CONFIG === "object") {
        var merged = {};
        for (var k in defaults) merged[k] = defaults[k];
        for (var k in window.CONSENT_CONFIG) {
          if (Object.prototype.hasOwnProperty.call(window.CONSENT_CONFIG, k) && k !== "endpoints") {
            merged[k] = window.CONSENT_CONFIG[k];
          }
        }
        merged.endpoints = Object.assign({}, defaults.endpoints, window.CONSENT_CONFIG.endpoints || {});
        return merged;
      }
    } catch (e) {}
    return defaults;
  })();

  var COOKIE_NAME = String(config.cookieName || defaults.cookieName);
  var LS_KEY = String(config.localStorageKey || defaults.localStorageKey);
  var endpoints = Object.assign({}, defaults.endpoints, config.endpoints || {});
  var SLOT_ID = config.bannerSlotId || defaults.bannerSlotId;
  var BANNER_ID = config.bannerId || defaults.bannerId;
  var TOASTS_ID = config.toastsId || defaults.toastsId;
  var AUTO_LOAD = typeof config.autoLoad !== "undefined" ? !!config.autoLoad : defaults.autoLoad;

  // -------------------------------------------------------------------------
  // Cookie & Storage Helpers
  // -------------------------------------------------------------------------

  function getCookie(name) {
    try {
      if (!name || typeof document === "undefined" || !document.cookie) return null;
      var cookies = document.cookie.split(";");
      for (var i = 0; i < cookies.length; i++) {
        var c = cookies[i].trim();
        if (c.indexOf(name + "=") === 0) {
          return decodeURIComponent(c.substring(name.length + 1));
        }
      }
    } catch (e) {
      console.debug("consent-banner-loader.getCookie error:", e);
    }
    return null;
  }

  function getLocalStorage(key) {
    try {
      return localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function setLocalStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch (e) {}
  }

  /**
   * Check if user has given consent via cookie OR localStorage.
   * Returns true if any consent category is truthy.
   */
  function hasConsentGiven() {
    try {
      // 1. Check localStorage first (fastest, most reliable)
      var lsVal = getLocalStorage(LS_KEY);
      if (lsVal === "1" || lsVal === "true") return true;

      // 2. Check cookie
      var cookieVal = getCookie(COOKIE_NAME);
      if (!cookieVal) return false;

      // Simple values
      if (cookieVal === "1" || cookieVal === "true") {
        // Sync to localStorage for faster future checks
        setLocalStorage(LS_KEY, "1");
        return true;
      }

      // JSON object (e.g., {"functional":true,"analytics":false})
      try {
        var parsed = JSON.parse(cookieVal);
        if (parsed && typeof parsed === "object") {
          for (var key in parsed) {
            if (Object.prototype.hasOwnProperty.call(parsed, key) && parsed[key]) {
              // At least one category is accepted - sync to localStorage
              setLocalStorage(LS_KEY, "1");
              return true;
            }
          }
        }
      } catch (parseErr) {}

      return false;
    } catch (e) {
      console.debug("consent-banner-loader.hasConsentGiven error:", e);
      return false;
    }
  }

  /**
   * Sync consent to localStorage after accept/reject.
   * This ensures the banner doesn't reappear on page navigation.
   */
  function syncConsentToLocalStorage(accepted) {
    try {
      setLocalStorage(LS_KEY, accepted ? "1" : "0");
      // Also sync with window.gsmConsent if available
      if (window.gsmConsent && typeof window.gsmConsent.set === "function") {
        window.gsmConsent.set(accepted);
      }
      // Remove needs-consent class from body
      if (accepted && document.body) {
        document.body.classList.remove("needs-consent");
      }
    } catch (e) {}
  }

  // -------------------------------------------------------------------------
  // CSRF Token
  // -------------------------------------------------------------------------

  function getCSRFToken() {
    try {
      var meta = document.querySelector('meta[name="csrf-token"]') ||
                 document.querySelector('meta[name="csrfmiddlewaretoken"]') ||
                 document.querySelector('meta[name="X-CSRFToken"]');
      return meta ? meta.content : null;
    } catch (e) {
      return null;
    }
  }

  function fetchWithCSRF(url, options) {
    options = options || {};
    var headers = new Headers(options.headers || {});

    try {
      if (!headers.has("X-Requested-With")) {
        headers.set("X-Requested-With", "XMLHttpRequest");
      }
    } catch (e) {}

    try {
      var csrfToken = null;
      try {
        csrfToken = window.AppUI && typeof window.AppUI.getCsrfToken === "function"
          ? window.AppUI.getCsrfToken() : null;
      } catch (e) {}
      csrfToken = csrfToken || getCookie("csrftoken") || getCSRFToken();
      if (csrfToken && !headers.has("X-CSRFToken")) {
        headers.set("X-CSRFToken", csrfToken);
      }
    } catch (e) {}

    return fetch(url, {
      method: options.method || "GET",
      credentials: "same-origin",
      headers: headers,
      body: options.body || null
    });
  }

  // -------------------------------------------------------------------------
  // DOM Helpers
  // -------------------------------------------------------------------------

  function sanitizeFragment(fragment) {
    try {
      if (!fragment || !fragment.querySelectorAll) return;
      // Remove scripts
      fragment.querySelectorAll("script").forEach(function(s) {
        if (s.parentNode) s.parentNode.removeChild(s);
      });
      // Whitelist safe elements
      var allowed = {DIV:1,P:1,SPAN:1,BUTTON:1,A:1,UL:1,LI:1,INPUT:1,LABEL:1,SECTION:1,ARTICLE:1,FORM:1};
      fragment.querySelectorAll("*").forEach(function(el) {
        if (!allowed[el.tagName]) {
          el.remove();
          return;
        }
        // Remove event handlers
        for (var i = el.attributes.length - 1; i >= 0; i--) {
          var name = el.attributes[i].name;
          var val = el.attributes[i].value || "";
          if (/^on/i.test(name)) {
            el.removeAttribute(name);
            continue;
          }
          if (/^(href|src)$/i.test(name) && (/^\s*javascript:/i.test(val) || /^\s*data:text\/html/i.test(val))) {
            el.removeAttribute(name);
          }
        }
      });
    } catch (e) {
      console.debug("consent-banner-loader.sanitizeFragment:", e);
    }
  }

  function ensureSlot() {
    try {
      var slot = document.getElementById(SLOT_ID);
      if (!slot) {
        var banner = document.getElementById(BANNER_ID);
        if (banner && banner.parentElement) {
          slot = banner.parentElement;
        }
      }
      if (!slot) {
        slot = document.createElement("div");
        slot.id = SLOT_ID;
        slot.style.position = "relative";
        slot.style.zIndex = 99999;
        (document.body || document.documentElement).appendChild(slot);
      }
      return slot;
    } catch (e) {
      console.debug("consent-banner-loader.ensureSlot:", e);
      return null;
    }
  }

  function removeBanner() {
    try {
      var banner = document.getElementById(BANNER_ID);
      if (banner && banner.parentElement) {
        banner.parentElement.removeChild(banner);
      }
      var slot = document.getElementById(SLOT_ID);
      if (slot && !slot.hasChildNodes() && slot.parentElement) {
        slot.parentElement.removeChild(slot);
      }
    } catch (e) {
      console.debug("consent-banner-loader.removeBanner:", e);
    }
  }

  function renderBanner(html) {
    try {
      if (!html || typeof html !== "string") return;
      var slot = ensureSlot();
      if (!slot) return;

      var template = document.createElement("template");
      template.innerHTML = html.trim();
      var fragment = template.content.cloneNode(true);
      sanitizeFragment(fragment);

      var newBanner = fragment.firstElementChild || null;
      var existingBanner = document.getElementById(BANNER_ID);

      if (existingBanner && newBanner) {
        try {
          if (existingBanner.isEqualNode(newBanner)) return;
        } catch (e) {}
        if (existingBanner.parentNode) {
          existingBanner.parentNode.removeChild(existingBanner);
        }
      }

      while (slot.firstChild) slot.removeChild(slot.firstChild);
      slot.appendChild(fragment);
      attachHandlers();
    } catch (e) {
      console.error("consent-banner-loader.renderBanner:", e);
    }
  }

  // -------------------------------------------------------------------------
  // Toast Notifications
  // -------------------------------------------------------------------------

  function ensureToastContainer() {
    try {
      var container = document.getElementById(TOASTS_ID);
      if (!container) {
        container = document.createElement("div");
        container.id = TOASTS_ID;
        container.style.position = "fixed";
        container.style.top = "16px";
        container.style.right = "16px";
        container.style.zIndex = 100000;
        document.body.appendChild(container);
      }
      return container;
    } catch (e) {
      return null;
    }
  }

  function showToast(message) {
    try {
      if (!message) return;
      var container = ensureToastContainer();
      if (!container) return;

      var toast = document.createElement("div");
      toast.className = "toast show bg-dark text-white p-3 mb-2 rounded shadow-lg";
      toast.textContent = String(message);
      container.appendChild(toast);

      setTimeout(function() {
        try { toast.remove(); } catch (e) {}
      }, 3500);
    } catch (e) {}
  }

  // -------------------------------------------------------------------------
  // Button Handlers
  // -------------------------------------------------------------------------

  function findButton(container, action) {
    try {
      if (!container || !container.querySelector) return null;
      return container.querySelector('[data-consent-action="' + action + '"]') ||
             container.querySelector("#" + action.replace(/\W/g, "-")) ||
             null;
    } catch (e) {
      return null;
    }
  }

  function attachHandlers() {
    try {
      var banner = document.getElementById(BANNER_ID);
      if (!banner || (banner.dataset && banner.dataset.handlersAttached === "1")) return;
      if (banner.dataset) banner.dataset.handlersAttached = "1";

      var acceptBtn = findButton(banner, "accept-all");
      var rejectBtn = findButton(banner, "reject-all");
      var closeBtn = findButton(banner, "close");

      if (acceptBtn && !acceptBtn._attached) {
        acceptBtn.addEventListener("click", function(e) {
          e.preventDefault();
          doAcceptAll();
        });
        acceptBtn._attached = true;
      }

      if (rejectBtn && !rejectBtn._attached) {
        rejectBtn.addEventListener("click", function(e) {
          e.preventDefault();
          doRejectAll();
        });
        rejectBtn._attached = true;
      }

      if (closeBtn && !closeBtn._attached) {
        closeBtn.addEventListener("click", function(e) {
          e.preventDefault();
          removeBanner();
        });
        closeBtn._attached = true;
      }

      // Granular checkboxes
      var checkboxes = banner.querySelectorAll('input[type="checkbox"][data-consent-slug]') || [];
      if (!checkboxes.length) {
        checkboxes = banner.querySelectorAll('input[type="checkbox"]') || [];
      }
      for (var i = 0; i < checkboxes.length; i++) {
        (function(cb) {
          if (cb._attached) return;
          cb.addEventListener("change", function() {
            if (window.__consent_save_timeout) clearTimeout(window.__consent_save_timeout);
            window.__consent_save_timeout = setTimeout(saveGranularPreferences, 250);
          });
          cb._attached = true;
        })(checkboxes[i]);
      }
    } catch (e) {
      console.debug("consent-banner-loader.attachHandlers:", e);
    }
  }

  async function doAcceptAll() {
    try {
      var response = await fetchWithCSRF(endpoints.acceptAll, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        body: new URLSearchParams({ accept_all: "1" }).toString()
      });

      // CRITICAL FIX: Sync to localStorage BEFORE removing banner
      syncConsentToLocalStorage(true);

      var text = "";
      try { text = await response.text(); } catch (e) {}

      removeBanner();

      try {
        var json = JSON.parse(text || "{}");
        if (json && json.message) showToast(json.message);
      } catch (e) {}

    } catch (e) {
      console.error("consent-banner-loader.doAcceptAll:", e);
      showToast("Failed to accept cookies — please try again.");
    }
  }

  async function doRejectAll() {
    try {
      var response = await fetchWithCSRF(endpoints.rejectAll, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
        body: new URLSearchParams({ reject_all: "1" }).toString()
      });

      // Even rejecting sets a consent decision (functional only)
      // Sync to prevent banner from reappearing
      syncConsentToLocalStorage(true);

      var text = "";
      try { text = await response.text(); } catch (e) {}

      removeBanner();

      try {
        var json = JSON.parse(text || "{}");
        if (json && json.message) showToast(json.message);
      } catch (e) {}

    } catch (e) {
      console.error("consent-banner-loader.doRejectAll:", e);
      showToast("Failed to reject cookies — please try again.");
    }
  }

  async function saveGranularPreferences() {
    try {
      var banner = document.getElementById(BANNER_ID);
      if (!banner) return;

      var prefs = {};
      var checkboxes = banner.querySelectorAll('input[type="checkbox"][data-consent-slug]') || [];
      if (!checkboxes.length) {
        checkboxes = banner.querySelectorAll('input[type="checkbox"]') || [];
      }

      for (var i = 0; i < checkboxes.length; i++) {
        var cb = checkboxes[i];
        try {
          var slug = cb.getAttribute("data-consent-slug") ||
                     (cb.dataset && (cb.dataset.consentSlug || cb.dataset.consent_slug || cb.dataset.consent)) ||
                     cb.name || null;
          if (!slug) continue;
          prefs[String(slug)] = !!cb.checked;
        } catch (e) {}
      }

      var response = await fetchWithCSRF(endpoints.accept, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs)
      });

      if (!response || !response.ok) {
        console.warn("consent-banner-loader.saveGranularPreferences: server returned", response && response.status);
        return;
      }

      // Sync to localStorage
      syncConsentToLocalStorage(true);

      try {
        var json = await response.json();
        if (json && json.message) showToast(json.message);
      } catch (e) {
        var text = await response.text();
        if (text) showToast("Preferences saved");
      }
    } catch (e) {
      console.error("consent-banner-loader.saveGranularPreferences:", e);
    }
  }

  // -------------------------------------------------------------------------
  // Main Loader
  // -------------------------------------------------------------------------

  async function loadBanner() {
    try {
      // CRITICAL: Check consent FIRST, before making any network request
      if (hasConsentGiven()) {
        removeBanner();
        return;
      }

      var response = await fetchWithCSRF(endpoints.banner, { method: "GET" });
      if (!response || !response.ok) return;

      var html = await response.text();
      if (!html || !html.trim()) {
        removeBanner();
        return;
      }

      renderBanner(html);
    } catch (e) {
      console.error("consent-banner-loader.loadBanner:", e);
    }
  }

  // Initialize
  try {
    if (AUTO_LOAD) {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadBanner);
      } else {
        setTimeout(loadBanner, 0);
      }
    }
  } catch (e) {
    console.debug("consent-banner-loader.init:", e);
  }

  // Expose for external use
  window.AppConsent.load = loadBanner;
  window.AppConsent.remove = removeBanner;
  window.AppConsent.hasConsent = hasConsentGiven;

})();

// Apply consent-required class only when no valid consent is present.
(function() {
  try {
    // Check localStorage first (fastest)
    var lsConsent = false;
    try {
      lsConsent = localStorage.getItem("consent_ads") === "1";
    } catch (e) {}

    // Then check gsmConsent
    var gsmConsent = window.gsmConsent &&
                     typeof window.gsmConsent.get === "function" &&
                     window.gsmConsent.get();

    if (!lsConsent && !gsmConsent) {
      document.body.classList.add("needs-consent");
    }
  } catch (err) {
    console.error("Consent loader failed:", err);
    document.body.classList.add("needs-consent");
  }
})();
