
(function () {
  "use strict";

  const cache = new Map();
  const FONT_URDU = "Jameel Noori Nastaleeq, 'Noto Nastaliq Urdu', serif";
  const THEME_COOKIE = "theme_pref";
  const THEME_ORDER = ["light", "dark", "high_contrast"];
  const FALLBACK_TOKENS = {
    light: {
      color: {
        surface: "#ffffff",
        text: "#0f172a",
        muted: "#475569",
        border: "#e2e8f0",
        primary: "#0d6efd",
      },
    },
    dark: {
      color: {
        surface: "#0f172a",
        text: "#e2e8f0",
        muted: "#94a3b8",
        border: "#1f2937",
        primary: "#38bdf8",
      },
    },
    high_contrast: {
      color: {
        surface: "#000000",
        text: "#ffffff",
        muted: "#d1d5db",
        border: "#ffffff",
        primary: "#ffbf00",
      },
    },
  };

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(?:(?:^|.*;\\s*)" + name + "\\s*=\\s*([^;]*).*$)|^.*$"));
    return match && match[1] ? decodeURIComponent(match[1]) : null;
  }

  function setCookie(name, value, days) {
    const expires = new Date(Date.now() + (days || 365) * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options || {});
    if (!res.ok) throw new Error("Request failed: " + res.status);
    return res.json();
  }

  function applyDirection(dir) {
    const root = document.documentElement;
    root.setAttribute("dir", dir || "ltr");
    root.style.direction = dir || "ltr";
  }

  function applyFonts(tokens) {
    const root = document.documentElement;
    const fonts = (tokens && tokens.typography && tokens.typography.fonts) || {};
    if (fonts.urdu_base || fonts.urdu_heading) {
      root.style.setProperty("--font-urdu-base", fonts.urdu_base || FONT_URDU);
      root.style.setProperty("--font-urdu-heading", fonts.urdu_heading || FONT_URDU);
    }
  }

  function applyTokens(tokens) {
    if (!tokens) return;
    const root = document.documentElement;
    const flatten = (obj, prefix = "") => {
      Object.entries(obj || {}).forEach(([k, v]) => {
        const key = prefix ? `${prefix}-${k}` : k;
        if (v && typeof v === "object") {
          flatten(v, key);
        } else {
          root.style.setProperty(`--${key}`, v);
        }
      });
    };
    flatten(tokens);
    applyFonts(tokens);
  }

  function applyFallbackTheme(mode) {
    const tokens = FALLBACK_TOKENS[mode] || FALLBACK_TOKENS.light;
    applyTokens(tokens);
    const root = document.documentElement;
    root.dataset.theme = mode;
    root.style.colorScheme = mode === "dark" ? "dark" : "light";
  }

  async function loadBundle(appId, locale, namespaces) {
    const key = `${appId}:${locale}:${(namespaces || []).join(",")}`;
    if (cache.has(key)) return cache.get(key);
    const params = new URLSearchParams({ app_id: appId, locale });
    (namespaces || []).forEach((ns) => params.append("namespace", ns));
    const data = await fetchJson(`/i18n/bundle/?${params.toString()}`);
    cache.set(key, data);
    return data;
  }

  function createTranslator(bundle) {
    return (k, fallback) => {
      if (!bundle || !bundle.values) return fallback || k;
      return bundle.values[k] || fallback || k;
    };
  }

  async function initTheme(appId, route) {
    const params = new URLSearchParams({ app_id: appId, route: route || window.location.pathname });
    try {
      const data = await fetchJson(`/i18n/theme/?${params.toString()}`);
      if (data && data.tokens) {
        applyDirection(data.direction);
        const tokens = Object.keys(data.tokens || {}).length
          ? data.tokens
          : FALLBACK_TOKENS[data.mode] || FALLBACK_TOKENS.light;
        applyTokens(tokens);
      } else {
        applyFallbackTheme((data && data.mode) || "light");
      }
      if (data && data.mode) {
        const root = document.documentElement;
        root.dataset.theme = data.mode;
        root.style.colorScheme = data.mode === "dark" ? "dark" : "light";
      }
      return data;
    } catch (err) {
      console.warn("initTheme failed, using fallback", err);
      const pref = (getCookie(THEME_COOKIE) || "light").toLowerCase();
      applyFallbackTheme(pref);
      return null;
    }
  }

  async function loadTranslations(appId, locale, namespaces) {
    const key = `${appId}:${locale}:${(namespaces || []).join(",")}`;
    if (cache.has(key)) return cache.get(key);
    const params = new URLSearchParams({ app_id: appId, locale });
    (namespaces || []).forEach((ns) => params.append("namespace", ns));
    const data = await fetchJson(`/i18n/bundle/?${params.toString()}`);
    cache.set(key, data);
    return data;
  }

  function t(bundle, key, fallback) {
    if (!bundle || !bundle.values) return fallback || key;
    return bundle.values[key] || fallback || key;
  }

  window.I18nThemes = {
    loadBundle,
    createTranslator,
    initTheme,
    loadTranslations,
    t,
    applyDirection,
    applyFallbackTheme,
    setThemePreference(pref) {
      if (!pref) return;
      setCookie(THEME_COOKIE, pref, 365);
      // Refresh theme without full reload
      initTheme("core").catch(() => {});
    },
  };

  document.addEventListener("DOMContentLoaded", () => {
    const fab = document.getElementById("theme-fab");
    if (fab) {
      fab.addEventListener("click", async (e) => {
        e.preventDefault();
        const current = (getCookie(THEME_COOKIE) || "").toLowerCase();
        const idx = THEME_ORDER.indexOf(current);
        const next = THEME_ORDER[(idx + 1) % THEME_ORDER.length];
        setCookie(THEME_COOKIE, next, 365);
        try {
          await initTheme("core");
        } catch (err) {
          console.warn("Theme toggle failed", err);
        }
      });
    }
  });
})();


