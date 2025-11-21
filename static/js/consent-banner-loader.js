// static/js/consent-banner-loader.js
// Hardened, CSP-safe, enterprise-grade Consent Banner Loader (final version)

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  //  A: Idempotent loader guard & runtime CONFIG
  // ---------------------------------------------------------------------------
  if (typeof window !== "undefined" && window.__CONSENT_BANNER_LOADER_LOADED__) return;
  if (typeof window !== "undefined") window.__CONSENT_BANNER_LOADER_LOADED__ = true;

  // Safe namespace
  window.AppConsent = window.AppConsent || {};

  var DEFAULTS = {
    cookieName: "consent_status",
    endpoints: {
      banner: "/consent/banner/",
      acceptAll: "/consent/accept_all/",
      rejectAll: "/consent/reject_all/",
      accept: "/consent/accept/",
    },
    bannerSlotId: "consent-banner-slot",
    bannerId: "consent-banner",
    toastsId: "app-toasts",
    autoLoad: true,
  };

  // ---------------------------------------------------------------------------
  //  Runtime Configuration Merge (safe)
  // ---------------------------------------------------------------------------
  var CONFIG = (function () {
    try {
      if (
        typeof window !== "undefined" &&
        window.CONSENT_CONFIG &&
        typeof window.CONSENT_CONFIG === "object"
      ) {
        var merged = {};
        for (var k in DEFAULTS) merged[k] = DEFAULTS[k];

        for (var key in window.CONSENT_CONFIG) {
          if (
            Object.prototype.hasOwnProperty.call(window.CONSENT_CONFIG, key) &&
            key !== "endpoints"
          ) {
            merged[key] = window.CONSENT_CONFIG[key];
          }
        }

        merged.endpoints = Object.assign(
          {},
          DEFAULTS.endpoints,
          window.CONSENT_CONFIG.endpoints || {}
        );

        return merged;
      }
    } catch (_) {}

    return DEFAULTS;
  })();

  var CONSENT_COOKIE_NAME = String(CONFIG.cookieName || DEFAULTS.cookieName);
  var ENDPOINTS = Object.assign({}, DEFAULTS.endpoints, CONFIG.endpoints || {});
  var BANNER_SLOT_ID = CONFIG.bannerSlotId || DEFAULTS.bannerSlotId;
  var BANNER_ID = CONFIG.bannerId || DEFAULTS.bannerId;
  var TOASTS_ID = CONFIG.toastsId || DEFAULTS.toastsId;
  var AUTO_LOAD =
    typeof CONFIG.autoLoad !== "undefined"
      ? !!CONFIG.autoLoad
      : DEFAULTS.autoLoad;

  // ---------------------------------------------------------------------------
  //  Utilities
  // ---------------------------------------------------------------------------
  function getCookie(name) {
    try {
      if (!name || typeof document === "undefined" || !document.cookie) return null;
      var parts = document.cookie.split(";");
      for (var i = 0; i < parts.length; i++) {
        var cookie = parts[i].trim();
        if (cookie.indexOf(name + "=") === 0) {
          return decodeURIComponent(cookie.substring(name.length + 1));
        }
      }
    } catch (err) {
      console.debug("consent-banner-loader.getCookie error:", err);
    }
    return null;
  }

  function hasConsentCookie() {
    try {
      var v = getCookie(CONSENT_COOKIE_NAME);
      if (!v) return false;

      if (v === "1" || v === "true") return true;

      try {
        var parsed = JSON.parse(v);
        if (parsed && typeof parsed === "object") {
          for (var k in parsed) {
            if (!Object.prototype.hasOwnProperty.call(parsed, k)) continue;
            if (parsed[k]) return true;
          }
        }
      } catch (_) {}

      return false;
    } catch (err) {
      console.debug("consent-banner-loader.hasConsentCookie error:", err);
      return false;
    }
  }

  function getMetaCsrf() {
    try {
      var m =
        document.querySelector('meta[name="csrf-token"]') ||
        document.querySelector('meta[name="csrfmiddlewaretoken"]') ||
        document.querySelector('meta[name="X-CSRFToken"]') ||
        null;
      return m ? m.content : null;
    } catch (_) {
      return null;
    }
  }

  // Safe CSRF fetch wrapper
  function csrfFetch(url, opts) {
    opts = opts || {};
    var headers = new Headers(opts.headers || {});

    try {
      if (!headers.has("X-Requested-With"))
        headers.set("X-Requested-With", "XMLHttpRequest");
    } catch (_) {}

    try {
      var csrftoken = getCookie("csrftoken") || getMetaCsrf();
      if (csrftoken && !headers.has("X-CSRFToken")) {
        headers.set("X-CSRFToken", csrftoken);
      }
    } catch (_) {}

    return fetch(url, {
      method: opts.method || "GET",
      credentials: "same-origin",
      headers: headers,
      body: opts.body || null,
    });
  }

  // ---------------------------------------------------------------------------
  //  Whitelist-based Sanitization
  // ---------------------------------------------------------------------------
  function sanitizeFragment(root) {
    try {
      if (!root || !root.querySelectorAll) return;

      // Remove scripts entirely
      root.querySelectorAll("script").forEach(function (s) {
        if (s.parentNode) s.parentNode.removeChild(s);
      });

      // Whitelist tags allowed
      var ALLOWED_TAGS = {
        DIV: true,
        P: true,
        SPAN: true,
        BUTTON: true,
        A: true,
        UL: true,
        LI: true,
        INPUT: true,
        LABEL: true,
        SECTION: true,
        ARTICLE: true,
        FORM: true,
      };

      root.querySelectorAll("*").forEach(function (el) {
        // Remove non-whitelisted tags
        if (!ALLOWED_TAGS[el.tagName]) {
          el.remove();
          return;
        }

        // Strip dangerous attributes
        for (var i = el.attributes.length - 1; i >= 0; i--) {
          var name = el.attributes[i].name;
          var value = el.attributes[i].value || "";

          // Inline event handlers
          if (/^on/i.test(name)) {
            el.removeAttribute(name);
            continue;
          }

          // JS URLs
          if (/^(href|src)$/i.test(name)) {
            if (/^\s*javascript:/i.test(value) || /^\s*data:text\/html/i.test(value)) {
              el.removeAttribute(name);
            }
          }
        }
      });
    } catch (err) {
      console.debug("consent-banner-loader.sanitizeFragment:", err);
    }
  }

  // ---------------------------------------------------------------------------
  //  DOM helpers
  // ---------------------------------------------------------------------------
  function ensureSlot() {
    try {
      var slot = document.getElementById(BANNER_SLOT_ID);
      if (!slot) {
        var existingBanner = document.getElementById(BANNER_ID);
        if (existingBanner && existingBanner.parentElement) {
          slot = existingBanner.parentElement;
        }
      }
      if (!slot) {
        slot = document.createElement("div");
        slot.id = BANNER_SLOT_ID;
        slot.style.position = "relative";
        slot.style.zIndex = 99999;
        (document.body || document.documentElement).appendChild(slot);
      }
      return slot;
    } catch (err) {
      console.debug("consent-banner-loader.ensureSlot:", err);
      return null;
    }
  }

  function removeBanner() {
    try {
      var banner = document.getElementById(BANNER_ID);
      if (banner && banner.parentElement) banner.parentElement.removeChild(banner);

      var slot = document.getElementById(BANNER_SLOT_ID);
      if (slot && !slot.hasChildNodes() && slot.parentElement) {
        slot.parentElement.removeChild(slot);
      }
    } catch (err) {
      console.debug("consent-banner-loader.removeBanner:", err);
    }
  }

  // ---------------------------------------------------------------------------
  //  Render banner (duplicate protection, sanitized)
  // ---------------------------------------------------------------------------
  function renderBanner(html) {
    try {
      if (!html || typeof html !== "string") return;

      var slot = ensureSlot();
      if (!slot) return;

      var tpl = document.createElement("template");
      tpl.innerHTML = html.trim();

      var frag = tpl.content.cloneNode(true);
      sanitizeFragment(frag);

      var newBanner = frag.firstElementChild || null;
      var oldBanner = document.getElementById(BANNER_ID);

      if (oldBanner && newBanner) {
        try {
          if (oldBanner.isEqualNode(newBanner)) {
            return; // Skip identical
          }
        } catch (_) {}
        if (oldBanner.parentNode) oldBanner.parentNode.removeChild(oldBanner);
      }

      // Replace content
      while (slot.firstChild) slot.removeChild(slot.firstChild);
      slot.appendChild(frag);

      attachHandlers();
    } catch (err) {
      console.error("consent-banner-loader.renderBanner:", err);
    }
  }

  // ---------------------------------------------------------------------------
  //  Toast Helpers (CSP-safe)
  // ---------------------------------------------------------------------------
  function ensureToastsArea() {
    try {
      var area = document.getElementById(TOASTS_ID);
      if (!area) {
        area = document.createElement("div");
        area.id = TOASTS_ID;
        area.style.position = "fixed";
        area.style.top = "16px";
        area.style.right = "16px";
        area.style.zIndex = 100000;
        document.body.appendChild(area);
      }
      return area;
    } catch (_) {
      return null;
    }
  }

  function injectToastFromHtml(html) {
    try {
      if (!html) return;
      var tmp = document.createElement("div");
      tmp.innerHTML = html;

      var toastNode =
        tmp.querySelector(".toast") || tmp.querySelector(".toast-body");

      if (!toastNode) return;

      var toast = toastNode.cloneNode(true);
      sanitizeFragment(toast);

      var area = ensureToastsArea();
      if (!area) return;

      area.appendChild(toast);

      try {
        if (window.bootstrap && window.bootstrap.Toast) {
          new window.bootstrap.Toast(toast).show();
        } else {
          setTimeout(function () {
            try {
              toast.remove();
            } catch (_) {}
          }, 3500);
        }
      } catch (_) {
        setTimeout(function () {
          try {
            toast.remove();
          } catch (_) {}
        }, 3500);
      }
    } catch (err) {
      console.debug("consent-banner-loader.injectToastFromHtml:", err);
    }
  }

  function showToastMessage(msg) {
    try {
      if (!msg) return;
      var area = ensureToastsArea();
      if (!area) return;

      var t = document.createElement("div");
      t.className = "toast show bg-dark text-white p-3 mb-2 rounded shadow-lg";
      t.textContent = String(msg);

      area.appendChild(t);

      setTimeout(function () {
        try {
          t.remove();
        } catch (_) {}
      }, 3500);
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  //  Action / Checkbox helpers
  // ---------------------------------------------------------------------------
  function pickAction(root, name) {
    try {
      if (!root || !root.querySelector) return null;

      return (
        root.querySelector('[data-consent-action="' + name + '"]') ||
        root.querySelector('[data-hx-action="' + name + '"]') ||
        root.querySelector("#" + name.replace(/\W/g, "-")) ||
        null
      );
    } catch (_) {
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  //  Attach event handlers
  // ---------------------------------------------------------------------------
  function attachHandlers() {
    try {
      var banner = document.getElementById(BANNER_ID);
      if (!banner) return;

      if (banner.dataset && banner.dataset.handlersAttached === "1") return;
      if (banner.dataset) banner.dataset.handlersAttached = "1";

      var acceptBtn = pickAction(banner, "accept-all");
      var rejectBtn = pickAction(banner, "reject-all");
      var closeBtn = pickAction(banner, "close");

      if (acceptBtn && !acceptBtn._attached) {
        acceptBtn.addEventListener("click", function (e) {
          e.preventDefault();
          doAcceptAll();
        });
        acceptBtn._attached = true;
      }

      if (rejectBtn && !rejectBtn._attached) {
        rejectBtn.addEventListener("click", function (e) {
          e.preventDefault();
          doRejectAll();
        });
        rejectBtn._attached = true;
      }

      if (closeBtn && !closeBtn._attached) {
        closeBtn.addEventListener("click", function (e) {
          e.preventDefault();
          removeBanner();
        });
        closeBtn._attached = true;
      }

      // Checkbox collection
      var chks =
        banner.querySelectorAll(
          'input[type="checkbox"][data-consent-slug]'
        ) || [];
      if (!chks.length)
        chks = banner.querySelectorAll('input[type="checkbox"]') || [];

      for (var i = 0; i < chks.length; i++) {
        (function (chk) {
          if (chk._attached) return;
          chk.addEventListener("change", function () {
            if (window.__consent_save_timeout)
              clearTimeout(window.__consent_save_timeout);
            window.__consent_save_timeout = setTimeout(
              saveGranularPreferences,
              250
            );
          });
          chk._attached = true;
        })(chks[i]);
      }
    } catch (err) {
      console.debug("consent-banner-loader.attachHandlers:", err);
    }
  }

  // ---------------------------------------------------------------------------
  //  ACTIONS
  // ---------------------------------------------------------------------------
  async function doAcceptAll() {
    try {
      var res = await csrfFetch(ENDPOINTS.acceptAll, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: new URLSearchParams({ accept_all: "1" }).toString(),
      });

      var text = "";
      try {
        text = await res.text();
      } catch (_) {}

      removeBanner();

      try {
        var js = JSON.parse(text || "{}");
        if (js && js.message) showToastMessage(js.message);
        else injectToastFromHtml(text);
      } catch (_) {
        injectToastFromHtml(text);
      }
    } catch (err) {
      console.error("consent-banner-loader.doAcceptAll:", err);
      showToastMessage("Failed to accept cookies — please try again.");
    }
  }

  async function doRejectAll() {
    try {
      var res = await csrfFetch(ENDPOINTS.rejectAll, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        },
        body: new URLSearchParams({ reject_all: "1" }).toString(),
      });

      var text = "";
      try {
        text = await res.text();
      } catch (_) {}

      removeBanner();

      try {
        var js = JSON.parse(text || "{}");
        if (js && js.message) showToastMessage(js.message);
        else injectToastFromHtml(text);
      } catch (_) {
        injectToastFromHtml(text);
      }
    } catch (err) {
      console.error("consent-banner-loader.doRejectAll:", err);
      showToastMessage("Failed to reject cookies — please try again.");
    }
  }

  async function saveGranularPreferences() {
    try {
      var banner = document.getElementById(BANNER_ID);
      if (!banner) return;

      var payload = {};
      var chks =
        banner.querySelectorAll(
          'input[type="checkbox"][data-consent-slug]'
        ) || [];
      if (!chks.length)
        chks = banner.querySelectorAll('input[type="checkbox"]') || [];

      for (var i = 0; i < chks.length; i++) {
        var c = chks[i];
        try {
          var slug =
            c.getAttribute("data-consent-slug") ||
            (c.dataset &&
              (c.dataset.consentSlug ||
                c.dataset.consent_slug ||
                c.dataset.consent)) ||
            c.name ||
            null;
          if (!slug) continue;
          payload[String(slug)] = !!c.checked;
        } catch (_) {}
      }

      var res = await csrfFetch(ENDPOINTS.accept, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res || !res.ok) {
        console.warn(
          "consent-banner-loader.saveGranularPreferences: server returned",
          res && res.status
        );
        return;
      }

      try {
        var js = await res.json();
        if (js && js.message) {
          showToastMessage(js.message);
        }
      } catch (_) {
        var html = await res.text();
        injectToastFromHtml(html);
      }
    } catch (err) {
      console.error("consent-banner-loader.saveGranularPreferences:", err);
    }
  }

  // ---------------------------------------------------------------------------
  //  Load banner
  // ---------------------------------------------------------------------------
  async function loadBanner() {
    try {
      if (hasConsentCookie()) {
        removeBanner();
        return;
      }

      var res = await csrfFetch(ENDPOINTS.banner, { method: "GET" });
      if (!res || !res.ok) return;

      var html = await res.text();
      if (!html || !html.trim()) {
        removeBanner();
        return;
      }

      renderBanner(html);
    } catch (err) {
      console.error("consent-banner-loader.loadBanner:", err);
    }
  }

  // ---------------------------------------------------------------------------
  //  Auto-load
  // ---------------------------------------------------------------------------
  try {
    if (AUTO_LOAD) {
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", loadBanner);
      } else {
        setTimeout(loadBanner, 0);
      }
    }
  } catch (err) {
    console.debug("consent-banner-loader.init:", err);
  }
})();