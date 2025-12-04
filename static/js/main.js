
(() => {
  "use strict";

  const AppUI = (window.AppUI = window.AppUI || {});
  const doc = document;

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
    if (typeof initAuthToggle === "function") initAuthToggle();
    if (typeof initNotifications === "function") initNotifications();
    startNotifyPoll();
    initAccountActions();
    if (window.AppUI && typeof window.AppUI.bindAiHelpers === "function") {
      window.AppUI.bindAiHelpers();
    }
  }

  // DOM readiness flag with safety guarantees.
  document.addEventListener("DOMContentLoaded", () => {
    try {
      window.__ready = true;
    } catch (e) {
      console.error("Failed setting __ready flag", e);
    }
  });

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

// ------------------------------------------------------------------


