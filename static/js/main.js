(() => {
  "use strict";

  const AppUI = (window.AppUI = window.AppUI || {});
  const doc = document;

  // ------------------------------------------------------------
  // Device fingerprint: persist in localStorage + cookie (Secure on HTTPS)
  // ------------------------------------------------------------
  function setDeviceFpCookie(fp) {
    try {
      window.localStorage && window.localStorage.setItem("device_fp", fp);
    } catch (_) {
      /* ignore */
    }
    const expires = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toUTCString();
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `device_fp=${encodeURIComponent(fp)}; expires=${expires}; path=/; SameSite=Lax${secure}`;
  }

  function getDeviceFp() {
    try {
      const v = window.localStorage && window.localStorage.getItem("device_fp");
      if (v) return v;
    } catch (_) {
      /* ignore */
    }
    const m = doc.cookie.match(/(?:^|;)\s*device_fp=([^;]+)/);
    return m && m[1] ? decodeURIComponent(m[1]) : null;
  }

  function ensureDeviceFp() {
    let fp = getDeviceFp();
    if (!fp) {
      fp = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
      setDeviceFpCookie(fp);
    }

    // Inject hidden input into auth forms (login, signup, password reset/change)
    const authFormPattern = /(account[_/-](login|signup|password_(reset|change))|login|signup|password[_-](reset|change))/i;
    doc.querySelectorAll("form").forEach((form) => {
      const methodOk = form.method && form.method.toLowerCase() === "post";
      const hinted = form.dataset.deviceFp === "true";
      const actionMatch = form.action && authFormPattern.test(form.action);
      const idMatch = form.id && authFormPattern.test(form.id);
      const classMatch = form.className && authFormPattern.test(form.className);
      if (methodOk && (hinted || actionMatch || idMatch || classMatch)) {
        addFpInput(form, fp);
      }
    });
  }

  function addFpInput(form, fp) {
    if (!form || !fp || form.querySelector('input[name="device_fp"]')) return;
    const input = doc.createElement("input");
    input.type = "hidden";
    input.name = "device_fp";
    input.value = fp;
    form.appendChild(input);
  }

  // ------------------------------------------------------------
  // Utilities
  // ------------------------------------------------------------
  function safeQuery(id) {
    if (!id || typeof id !== "string") return null;
    try {
      return doc.getElementById(id) || null;
    } catch (err) {
      console.warn("main.js: safeQuery failed:", err);
      return null;
    }
  }

  function getCookie(name) {
    if (!document.cookie || document.cookie === "") return null;
    const parts = document.cookie.split(";");
    for (let i = 0; i < parts.length; i++) {
      const c = parts[i].trim();
      if (c.substring(0, name.length + 1) === name + "=") {
        return decodeURIComponent(c.substring(name.length + 1));
      }
    }
    return null;
  }

  function getCsrfToken() {
    let token = getCookie("csrftoken");
    if (token) return token;
    const meta =
      doc.querySelector('meta[name="csrf-token"]') ||
      doc.querySelector('meta[name="csrfmiddlewaretoken"]') ||
      doc.querySelector('meta[name="csrf"]');
    return meta && meta.content ? meta.content : null;
  }

  AppUI.getCsrfToken = getCsrfToken;

  function appendMessage(container, text, role = "bot") {
    if (!container) return null;
    const el = doc.createElement("div");
    el.textContent = typeof text === "string" ? text : String(text || "");
    el.className =
      role === "user"
        ? "small text-end p-2 user-message"
        : "small text-muted p-2 bot-message";
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
  }

  // Notifications bell (minimal fetcher)
  // ------------------------------------------------------------
  AppUI.loadNotifications = function () {
    const panel = safeQuery("notify-panel");
    const list = safeQuery("notify-list");
    const badge = safeQuery("notify-badge");
    const markAllBtn = safeQuery("notify-mark-all");
    if (!panel || !list || !badge) return;

    if (markAllBtn && !markAllBtn.dataset.bound) {
      markAllBtn.dataset.bound = "true";
      markAllBtn.addEventListener("click", () => {
        fetch("/notifications/mark-all/", {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCsrfToken() || "",
          },
          credentials: "include",
        })
          .then((res) => {
            if (!res.ok) throw new Error("HTTP " + res.status);
            list.innerHTML =
              '<div class="p-3 text-sm text-slate-500">All caught up.</div>';
            badge.classList.add("hidden");
          })
          .catch(() => {
            AppUI.showToast &&
              AppUI.showToast("Unable to mark notifications as read.", "Error");
          });
      });
    }

    fetch("/users/notifications/unread.json", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then((payload) => {
        const items = (payload && payload.items) || [];
        list.innerHTML = "";
        if (!items.length) {
          list.innerHTML =
            '<div class="p-3 text-sm text-slate-500">No new notifications.</div>';
          badge.classList.add("hidden");
          return;
        }
        items.forEach((n) => {
          const el = doc.createElement("div");
          el.className = "p-3 text-sm";
          el.innerHTML =
            '<div class="font-semibold text-slate-800">' +
            (n.title || "Notification") +
            "</div>" +
            '<div class="text-slate-600 text-xs mt-1">' +
            (n.message || "") +
            "</div>";
          list.appendChild(el);
        });
        badge.textContent = String(items.length);
        badge.classList.remove("hidden");
      })
      .catch((err) => {
        console.warn("main.js: unable to load notifications:", err);
      });
  };

  doc.addEventListener("click", (ev) => {
    const toggle = ev.target.closest("[data-notify-toggle]");
    const panel = safeQuery("notify-panel");
    if (!panel) return;
    if (toggle) {
      ev.preventDefault();
      if (panel.classList.contains("hidden")) {
        panel.classList.remove("hidden");
        AppUI.loadNotifications();
      } else {
        panel.classList.add("hidden");
      }
    } else if (!ev.target.closest("#app-notifications")) {
      panel.classList.add("hidden");
    }
  });

  // Small poller to keep badge fresh without opening the panel
  let notifyPollStarted = false;
  function startNotifyPoll() {
    if (notifyPollStarted) return;
    const badge = safeQuery("notify-badge");
    if (!badge) return;
    notifyPollStarted = true;
    const updateBadge = () => {
      fetch("/users/notifications/unread.json", {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "include",
      })
        .then((res) => {
          if (!res.ok) throw new Error("HTTP " + res.status);
          return res.json();
        })
        .then((payload) => {
          const count = ((payload && payload.items) || []).length;
          if (count > 0) {
            badge.textContent = String(count);
            badge.classList.remove("hidden");
          } else {
            badge.classList.add("hidden");
          }
        })
        .catch(() => {
          /* silent */
        });
    };
    updateBadge();
    setInterval(updateBadge, 60000);
  }

  // ------------------------------------------------------------
  // Account actions (resend verification, change username)
  // ------------------------------------------------------------
  function initAccountActions() {
    const resendBtn = doc.getElementById("resend-verification-btn");
    if (resendBtn) {
      resendBtn.addEventListener("click", async () => {
        resendBtn.disabled = true;
        try {
          const resp = await fetch("/users/accounts/resend-verification/", {
            method: "POST",
            headers: { "X-CSRFToken": getCsrfToken() || "" },
            credentials: "same-origin",
          });
          const data = await resp.json().catch(() => ({}));
          AppUI.showToast(
            data.ok ? "Verification sent!" : "Unable to send verification.",
            data.ok ? "Success" : "Error"
          );
        } catch (err) {
          AppUI.showToast("Unable to send verification.", "Error");
        } finally {
          resendBtn.disabled = false;
        }
      });
    }

    const usernameForm = doc.getElementById("username-change-form");
    if (usernameForm) {
      usernameForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(usernameForm);
        try {
          const resp = await fetch("/users/accounts/change-username/", {
            method: "POST",
            body: formData,
            headers: { "X-CSRFToken": getCsrfToken() || "" },
            credentials: "same-origin",
          });
          const data = await resp.json().catch(() => ({}));
          if (data.ok) {
            AppUI.showToast("Username updated!", "Success");
            setTimeout(() => location.reload(), 600);
          } else {
            AppUI.showToast(data.error || "Unable to update username.", "Error");
          }
        } catch (err) {
          AppUI.showToast("Unable to update username.", "Error");
        }
      });
    }
  }

  // ------------------------------------------------------------
  // Init
  // ------------------------------------------------------------
  function init() {
    ensureDeviceFp();
    if (typeof initAuthToggle === "function") initAuthToggle();
    if (typeof initNotifications === "function") initNotifications();
    startNotifyPoll();
    initAccountActions();
    if (window.AppUI && typeof window.AppUI.bindAiHelpers === "function") {
      window.AppUI.bindAiHelpers();
    }
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

// ------------------------------------------------------------------
// Theme Designer (runtime theming with presets + custom colors)
// ------------------------------------------------------------------
(() => {
  const e = document,
    t = "app_theme_prefs_v1",
    n = e.documentElement,
    o = e.querySelector('meta[name="theme-color"]'),
    r = {
      name: "aurora",
      primary: "#0ea5a4",
      primary600: "#0a7f82",
      accent: "#6366f1",
      surface: "#f8fafc",
      surface2: "#ffffff",
      text: "#0f172a",
      muted: "#475569",
      border: "#e2e8f0",
      gradient: "linear-gradient(135deg, #0ea5a4, #6366f1)",
      shadow: "0 12px 32px rgba(15, 23, 42, 0.14)",
      radius: "0.85rem",
    },
    s = {
      aurora: { ...r },
      midnight: {
        name: "midnight",
        primary: "#22d3ee",
        primary600: "#06b6d4",
        accent: "#c084fc",
        surface: "#0b1220",
        surface2: "#111827",
        text: "#e5e7eb",
        muted: "#9ca3af",
        border: "#1f2937",
        gradient: "linear-gradient(135deg, #111827, #22d3ee)",
        shadow: "0 12px 40px rgba(0, 0, 0, 0.65)",
        radius: "0.95rem",
      },
      daylight: {
        name: "daylight",
        primary: "#f97316",
        primary600: "#ea580c",
        accent: "#22c55e",
        surface: "#fdf7f0",
        surface2: "#ffffff",
        text: "#0f172a",
        muted: "#475569",
        border: "#f3e8e2",
        gradient: "linear-gradient(135deg, #f97316, #22c55e)",
        shadow: "0 10px 30px rgba(249, 115, 22, 0.22)",
        radius: "0.85rem",
      },
      emerald: {
        name: "emerald",
        primary: "#22c55e",
        primary600: "#16a34a",
        accent: "#0ea5e9",
        surface: "#e8fff6",
        surface2: "#ffffff",
        text: "#0f172a",
        muted: "#3f4b61",
        border: "#c8eedc",
        gradient: "linear-gradient(135deg, #22c55e, #0ea5e9)",
        shadow: "0 12px 32px rgba(34, 197, 94, 0.24)",
        radius: "0.9rem",
      },
    },
    l = { ...r },
    i = (e) => `--theme-${e.replace(/([A-Z])/g, "-$1").toLowerCase()}`,
    c = (e = {}, r = !0) => {
      l = { ...l, ...e };
      Object.entries(l).forEach((e) => {
        let [t, o] = e;
        n.style.setProperty(i(t), o);
      }),
        (document.body.dataset.themeName = l.name || "custom"),
        o && l.surface && o.setAttribute("content", l.surface),
        r &&
          (function (e) {
            try {
              localStorage.setItem(t, JSON.stringify(e));
            } catch (e) {
              /* ignore */
            }
          })(l),
        p(),
        u();
    },
    d = () => {
      try {
        let e = localStorage.getItem(t);
        if (!e) return;
        let n = JSON.parse(e);
        n && "object" == typeof n && (l = { ...r, ...n });
      } catch (e) {
        /* ignore */
      }
    },
    a = e.getElementById("theme-drawer"),
    m = e.getElementById("theme-fab"),
    y = e.getElementById("theme-close"),
    f = e.getElementById("theme-apply"),
    h = e.getElementById("theme-reset"),
    g = () => Array.from(e.querySelectorAll("[data-theme-preset]")),
    b = {
      primary: e.getElementById("theme-primary-input"),
      accent: e.getElementById("theme-accent-input"),
      surface: e.getElementById("theme-surface-input"),
      text: e.getElementById("theme-text-input"),
    };
  function p() {
    g().forEach((e) => {
      let t = l.name && e.dataset.themePreset === l.name;
      e.classList.toggle("is-active", !!t);
    });
  }
  function u() {
    b.primary && (b.primary.value = l.primary || r.primary),
      b.accent && (b.accent.value = l.accent || r.accent),
      b.surface && (b.surface.value = l.surface || r.surface),
      b.text && (b.text.value = l.text || r.text);
  }
  const S = () => {
    const focusFirstInDrawer = () => {
      if (!a || a.classList.contains("hidden")) return;
      const first = a.querySelector(
        'input, button, [href], [tabindex]:not([tabindex="-1"])'
      );
      first && "function" == typeof first.focus && first.focus();
    };
    m &&
      m.addEventListener("click", () => {
        if (!a) return;
        a.classList.toggle("hidden");
        a.classList.contains("hidden") || focusFirstInDrawer();
      });
    y &&
      y.addEventListener("click", () => {
        a && a.classList.add("hidden");
        m && m.focus();
      });
    f &&
      f.addEventListener("click", () => {
        a && a.classList.add("hidden");
        m && m.focus();
      });
    h &&
      h.addEventListener("click", () => {
        c({ ...r, name: "aurora" });
      });
    g().forEach((e) => {
      e.addEventListener("click", () => {
        let t = e.dataset.themePreset;
        s[t] && c({ ...s[t] });
      });
    });
    Object.entries(b).forEach(([e, t]) => {
      t &&
        t.addEventListener("input", () => {
          let n = { ...l, [e]: t.value };
          "primary" === e &&
            ((n.gradient = `linear-gradient(135deg, ${t.value}, ${
              n.accent || l.accent || r.accent
            })`),
            (n.primary600 = t.value)),
            c(n);
        });
    });
    document.addEventListener("keyup", (e) => {
      "Escape" === e.key &&
        a &&
        !a.classList.contains("hidden") &&
        (a.classList.add("hidden"), m && m.focus());
    });
  };
  ("loading" === e.readyState
    ? e.addEventListener("DOMContentLoaded", () => {
        d(), c(l, !1), S();
      })
    : (d(), c(l, !1), S()));
})();
