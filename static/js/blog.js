(() => {
  "use strict";
  const doc = document;

  const getCsrf = () => {
    if (window.AppUI && typeof window.AppUI.getCsrfToken === "function") {
      return window.AppUI.getCsrfToken();
    }
    const meta = doc.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;
    const match = document.cookie.match(/(?:^|;)\s*csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  };

  async function fetchJson(url, options = {}) {
    const opts = {
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        ...(options.headers || {}),
      },
      ...options,
    };
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function renderCommentItem(c, depth = 0) {
    const el = doc.createElement("div");
    el.className = "border border-slate-100 rounded-lg p-3 bg-white";
    el.style.marginLeft = depth ? `${Math.min(depth, 3) * 12}px` : "0";
    const toxicity = c.metadata?.moderation?.label || "low";
    const modChip =
      toxicity === "high"
        ? `<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-[11px]">Toxicity</span>`
        : "";
    const status = c.status || "approved";
    const statusChip =
      status !== "approved"
        ? `<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[11px]">${status}</span>`
        : "";
    const aiChip =
      c.metadata && c.metadata.moderation
        ? `<span class="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-[11px]">AI</span>`
        : "";

    const header = doc.createElement("div");
    header.className = "flex items-center justify-between text-xs text-slate-500";
    const userSpan = doc.createElement("span");
    userSpan.textContent = `${c.user || "User"} · ${new Date(c.created_at).toLocaleString()}`;
    const actions = doc.createElement("span");
    actions.className = "flex items-center gap-2";
    actions.innerHTML = `${modChip}${statusChip}${aiChip}<button class="text-slate-500 hover:text-primary text-[11px]" data-comment-upvote="${c.id}">▲ ${c.score || 0}</button>`;
    header.appendChild(userSpan);
    header.appendChild(actions);

    const bodyP = doc.createElement("p");
    bodyP.className = "text-sm text-slate-800 mt-1";
    bodyP.textContent = c.body || "";

    el.appendChild(header);
    el.appendChild(bodyP);
    if (c.children && c.children.length) {
      c.children.forEach((child) => {
        el.appendChild(renderCommentItem(child, depth + 1));
      });
    }
    return el;
  }

  function renderComments(container, items) {
    if (!container) return;
    container.innerHTML = "";
    if (!items || !items.length) {
      container.innerHTML = '<p class="text-sm text-slate-600">No comments yet.</p>';
      return;
    }
    items.forEach((c) => {
      container.appendChild(renderCommentItem(c, 0));
    });
  }

  async function loadComments() {
    const container = doc.getElementById("comment-thread");
    if (!container) return;
    const slug = container.dataset.postSlug;
    if (!slug) return;
    const sortSel = doc.getElementById("comment-sort");
    const sort = sortSel ? sortSel.value : "new";
    try {
      const data = await fetchJson(`/comments/${slug}/list.json?sort=${encodeURIComponent(sort)}`);
      renderComments(container, data.items || []);
    } catch (err) {
      container.innerHTML = '<p class="text-sm text-red-600">Unable to load comments.</p>';
    }
  }

  function bindCommentForm() {
    const form = doc.getElementById("comment-form");
    if (!form) return;
    const slug = form.dataset.postSlug;
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const bodyField = form.querySelector("textarea[name='body']");
      const body = bodyField ? bodyField.value.trim() : "";
      if (!body) {
        bodyField && bodyField.focus();
        return;
      }
      const formData = new FormData();
      formData.append("body", body);
      try {
        const res = await fetchJson(`/comments/${slug}/add.json`, {
          method: "POST",
          headers: { "X-CSRFToken": getCsrf() },
          body: formData,
        });
        bodyField.value = "";
        const msg = res.message || (res.status === "approved" ? "Comment posted" : "Submitted for review");
        window.AppUI?.showToast?.(msg, "Success");
        loadComments();
      } catch (err) {
        window.AppUI?.showToast?.("Unable to post comment", "Error");
      }
    });
  }

  function bindCommentControls() {
    doc.addEventListener("click", async (ev) => {
      const upvoteBtn = ev.target.closest("[data-comment-upvote]");
      if (upvoteBtn) {
        ev.preventDefault();
        const commentId = upvoteBtn.getAttribute("data-comment-upvote");
        try {
          const data = await fetchJson(`/comments/upvote/${commentId}/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf() },
          });
          if (data.score !== undefined) {
            upvoteBtn.textContent = `▲ ${data.score}`;
          }
        } catch (err) {
          window.AppUI?.showToast?.("Unable to upvote", "Error");
        }
      }
    });
    const sortSel = doc.getElementById("comment-sort");
    if (sortSel) {
      sortSel.addEventListener("change", () => loadComments());
    }
  }

  function bindAutosave() {
    const form = doc.querySelector("form[data-autosave-url]");
    if (!form) return;
    const autosaveUrl = form.dataset.autosaveUrl;
    let timer;
    const trigger = () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const formData = new FormData(form);
        try {
          await fetchJson(autosaveUrl, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf() },
            body: formData,
          });
        } catch (err) {
          /* silent */
        }
      }, 1200);
    };
    form.querySelectorAll("input, textarea, select").forEach((el) => {
      el.addEventListener("input", trigger);
    });
  }

  function bindTagAutocomplete() {
    const select = doc.querySelector("select[name='tags']");
    if (!select) return;
    // Add a lightweight search input to fetch tags and append options.
    const wrapper = doc.createElement("div");
    wrapper.className = "space-y-1";
    const input = doc.createElement("input");
    input.type = "search";
    input.placeholder = "Search existing tags…";
    input.className = "w-full rounded border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-primary focus:ring-2 focus:ring-primary/20";
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(select);

    let fetchTimer;
    input.addEventListener("input", () => {
      clearTimeout(fetchTimer);
      const q = input.value.trim();
      if (q.length < 2) return;
      fetchTimer = setTimeout(async () => {
        try {
          const data = await fetchJson(`/tags/search?q=${encodeURIComponent(q)}`);
          const items = data.items || [];
          items.forEach((item) => {
            const exists = Array.from(select.options).some((o) => o.value === item.slug);
            if (!exists) {
              const opt = new Option(item.name, item.slug);
              select.add(opt);
            }
          });
        } catch (_) {
          /* silent */
        }
      }, 250);
    });
  }

  function bindAIButtons() {
    if (window.AppUI && typeof window.AppUI.bindAiHelpers === "function") {
      window.AppUI.bindAiHelpers();
    }
  }

  function init() {
    loadComments();
    bindCommentForm();
    bindAutosave();
    bindTagAutocomplete();
    bindAIButtons();
    bindCommentControls();
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
