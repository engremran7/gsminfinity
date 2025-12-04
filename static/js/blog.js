
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
    const isJson = res.headers.get("content-type")?.includes("application/json");
    const data = isJson ? await res.json().catch(() => null) : null;
    if (!res.ok) {
      const err = new Error(data?.error || res.statusText || `HTTP ${res.status}`);
      err.status = res.status;
      err.payload = data;
      throw err;
    }
    return data;
  }

  // Inline helper for AI tag suggestion button
  document.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-ai-action='suggest_tags']");
    if (!btn) return;
    ev.preventDefault();
    const targetId = btn.dataset.aiTarget || "id_body";
    const bodyEl = document.getElementById(targetId);
    if (!bodyEl) return;
    const text = (bodyEl.value || "").trim();
    if (!text) return;
    const csrf = getCsrf();
    try {
      const resp = await fetch("/tags/suggest/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
        },
        body: JSON.stringify({ text }),
      });
      if (!resp.ok) throw new Error("suggest_failed");
      const payload = await resp.json();
      const tagsInput = document.getElementById("id_tags");
      if (tagsInput && Array.isArray(payload.suggestions)) {
        tagsInput.value = payload.suggestions.join(", ");
      }
      const suggestionsEl = document.getElementById("tag-suggestions");
      if (suggestionsEl && Array.isArray(payload.suggestions)) {
        suggestionsEl.innerHTML = payload.suggestions
          .map(
            (t) =>
              `<span class="px-2 py-1 rounded-full bg-slate-100 border border-slate-200">${t}</span>`
          )
          .join("");
      }
    } catch (err) {
      console.warn("Tag suggestions failed", err);
    }
  });

function renderCommentItem(c, depth = 0, currentUserId = null) {
    const el = doc.createElement("div");
    el.dataset.commentId = c.id;
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
    header.className = "flex items-center justify-between text-xs text-slate-500 flex-wrap";
    const userSpan = doc.createElement("span");
    const edited = c.edited_at ? ` • edited ${new Date(c.edited_at).toLocaleString()}` : "";
    userSpan.textContent = `${c.user || "User"} • ${new Date(c.created_at).toLocaleString()}${edited}`;
    const actions = doc.createElement("span");
    actions.className = "flex items-center gap-2";
    actions.innerHTML = `${modChip}${statusChip}${aiChip}<button class="text-slate-500 hover:text-primary text-[11px]" data-comment-upvote="${c.id}">⇧ ${c.score || 0}</button><button class="text-slate-500 hover:text-amber-600 text-[11px]" data-comment-report="${c.id}">Report</button>`;
    if (c.is_owner || (currentUserId && String(currentUserId) === String(c.user_id))) {
      const editBtn = doc.createElement("button");
      editBtn.className = "text-slate-500 hover:text-primary text-[11px]";
      editBtn.setAttribute("data-comment-edit", c.id);
      editBtn.textContent = "Edit";
      actions.appendChild(editBtn);
    }
    header.appendChild(userSpan);
    header.appendChild(actions);

    const bodyP = doc.createElement("p");
    bodyP.className = "text-sm text-slate-800 mt-1 comment-body";
    bodyP.textContent = c.body || "";

    el.appendChild(header);
    el.appendChild(bodyP);
    if (c.children && c.children.length) {
      c.children.forEach((child) => {
        el.appendChild(renderCommentItem(child, depth + 1, currentUserId));
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
    const currentUserId = container.dataset.currentUserId || null;
    items.forEach((c) => {
      container.appendChild(renderCommentItem(c, 0, currentUserId));
    });
  }

  async function loadComments() {
    const container = doc.getElementById("comment-thread");
    if (!container) return;
    if (container.dataset.commentsAllowed === "false") return;
    const slug = container.dataset.postSlug;
    if (!slug) return;
    const sortSel = doc.getElementById("comment-sort");
    const sort = sortSel ? sortSel.value : "new";
    try {
      const data = await fetchJson(`/comments/${slug}/list.json?sort=${encodeURIComponent(sort)}`);
      renderComments(container, data.items || []);
    } catch (err) {
      if (err.status === 403 && err.payload?.error === "consent_required") {
        container.innerHTML =
          '<p class="text-sm text-amber-700">Comments are disabled until you enable the comments category in cookie settings.</p>';
      } else {
        container.innerHTML = '<p class="text-sm text-red-600">Unable to load comments.</p>';
      }
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
        if (err.status === 403 && err.payload?.error === "consent_required") {
          window.AppUI?.showToast?.("Comments are disabled until you enable the comments category.", "Info");
        } else {
          window.AppUI?.showToast?.("Unable to post comment", "Error");
        }
      }
    });
  }

  function bindCommentControls() {
    doc.addEventListener("click", async (ev) => {
      const upvoteBtn = ev.target.closest("[data-comment-upvote]");
      const reportBtn = ev.target.closest("[data-comment-report]");
      const editBtn = ev.target.closest("[data-comment-edit]");
      if (upvoteBtn) {
        ev.preventDefault();
        const commentId = upvoteBtn.getAttribute("data-comment-upvote");
        try {
          const data = await fetchJson(`/comments/upvote/${commentId}/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf() },
          });
          if (data.score !== undefined) {
            upvoteBtn.textContent = `^ ${data.score}`;
          }
        } catch (err) {
          if (err.status === 403 && err.payload?.error === "consent_required") {
            window.AppUI?.showToast?.("Enable comments cookies to use voting.", "Info");
          } else {
            window.AppUI?.showToast?.("Unable to upvote", "Error");
          }
        }
      } else if (reportBtn) {
        ev.preventDefault();
        const commentId = reportBtn.getAttribute("data-comment-report");
        try {
          const res = await fetchJson(`/comments/report/${commentId}/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf() },
          });
          if (res.ok) {
            window.AppUI?.showToast?.("Reported for review", "Info");
          }
        } catch (err) {
          if (err.status === 403 && err.payload?.error === "consent_required") {
            window.AppUI?.showToast?.("Enable comments cookies to report content.", "Info");
          } else {
            window.AppUI?.showToast?.("Unable to report comment", "Error");
          }
        }
      } else if (editBtn) {
        ev.preventDefault();
        const commentId = editBtn.getAttribute("data-comment-edit");
        const card = editBtn.closest("[data-comment-id]") || editBtn.closest(".border");
        if (!card) return;
        const bodyEl = card.querySelector(".comment-body");
        if (!bodyEl) return;
        const current = bodyEl.textContent || "";
        const editor = doc.createElement("div");
        editor.className = "mt-2 space-y-2";
        editor.innerHTML = `
          <textarea class="w-full border border-slate-200 rounded-md p-2 text-sm shadow-sm focus:border-primary focus:ring-2 focus:ring-primary/20" rows="3">${current}</textarea>
          <div class="flex items-center gap-2">
            <button type="button" class="btn-primary text-xs px-3 py-1 rounded" data-comment-save="${commentId}">Save</button>
            <button type="button" class="btn-outline text-xs px-3 py-1 rounded" data-comment-cancel-edit>Cancel</button>
          </div>
          <p class="text-[11px] text-slate-500">Edits allowed for 24h; history is retained for abuse review.</p>
        `;
        bodyEl.replaceWith(editor);
      } else if (ev.target.closest("[data-comment-cancel-edit]")) {
        ev.preventDefault();
        loadComments();
      } else if (ev.target.closest("[data-comment-save]")) {
        ev.preventDefault();
        const saveBtn = ev.target.closest("[data-comment-save]");
        const commentId = saveBtn.getAttribute("data-comment-save");
        const editor = saveBtn.closest("div");
        const textarea = editor?.querySelector("textarea");
        const body = textarea?.value.trim();
        if (!body) return;
        const formData = new FormData();
        formData.append("body", body);
        try {
          const res = await fetchJson(`/comments/edit/${commentId}/`, {
            method: "POST",
            headers: { "X-CSRFToken": getCsrf() },
            body: formData,
          });
          if (res.ok) {
            window.AppUI?.showToast?.("Comment updated", "Success");
            loadComments();
          }
        } catch (err) {
          if (err.status === 400 && err.payload?.error === "edit_window_expired") {
            window.AppUI?.showToast?.("Edit window expired (24h).", "Info");
          } else if (err.status === 403) {
            window.AppUI?.showToast?.("Not allowed to edit this comment.", "Error");
          } else {
            window.AppUI?.showToast?.("Unable to edit comment", "Error");
          }
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
        const bodyField = form.querySelector("textarea[name='body']");
        if (bodyField) {
          bodyField.value = getBodyContent();
        }
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
    // Add a lightweight search input to fetch tags and a visible chip picker.
    const wrapper = doc.createElement("div");
    wrapper.className = "space-y-2";
    const input = doc.createElement("input");
    input.type = "search";
    input.placeholder = "Search existing tags.";
    input.className = "w-full rounded border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-primary focus:ring-2 focus:ring-primary/20";
    const resultsBox = doc.createElement("div");
    resultsBox.id = "tag-autocomplete-results";
    resultsBox.className = "flex flex-wrap gap-2 text-xs";
    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(select);
    wrapper.appendChild(resultsBox);

    const renderResults = (items) => {
      resultsBox.innerHTML = "";
      if (!items.length) {
        resultsBox.innerHTML = '<span class="text-slate-500">No matches.</span>';
        return;
      }
      items.forEach((item) => {
        const btn = doc.createElement("button");
        btn.type = "button";
        btn.className =
          "inline-flex items-center gap-2 px-2 py-1 rounded-full border border-slate-200 bg-white text-slate-700 hover:border-primary hover:text-primary transition";
        btn.innerHTML = `<span>${item.name}</span><span class="text-[10px] px-1.5 py-0.5 rounded ${item.is_curated ? "bg-emerald-100 text-emerald-700" : "bg-slate-800 text-white"}">${item.is_curated ? "Curated" : "Tag"}</span>`;
        btn.addEventListener("click", () => {
          let opt = Array.from(select.options).find((o) => o.value === item.slug);
          if (!opt) {
            opt = new Option(item.name, item.slug);
            select.add(opt);
          }
          opt.selected = true;
        });
        resultsBox.appendChild(btn);
      });
    };

    let fetchTimer;
    input.addEventListener("input", () => {
      clearTimeout(fetchTimer);
      const q = input.value.trim();
      if (q.length < 2) return;
      fetchTimer = setTimeout(async () => {
        try {
          const data = await fetchJson(`/tags/search?q=${encodeURIComponent(q)}`);
          const items = data.items || [];
          renderResults(items);
        } catch (_) {
          /* silent */
        }
      }, 250);
    });
  }

  function bindAIButtons() {
    doc.addEventListener("click", async (ev) => {
      const btn = ev.target.closest("[data-ai-action]");
      if (!btn) return;
      ev.preventDefault();
      const action = btn.getAttribute("data-ai-action");
      const targetSel = btn.getAttribute("data-ai-target") || "";
      const target = targetSel ? doc.querySelector(targetSel) : null;
      const payload = new FormData();
      payload.append("action", action);
      if (target && target.value) payload.append("text", target.value);
      const bodyVal = getBodyContent();
      if (bodyVal) {
        payload.append("context", bodyVal);
      }
      try {
        const res = await fetchJson("/blog/api/ai/assist/", {
          method: "POST",
          headers: { "X-CSRFToken": getCsrf() },
          body: payload,
        });
        if (res.ok && res.suggestion && target) {
          if (target.name === "body") {
            setBodyContent(res.suggestion);
          } else {
            target.value = res.suggestion;
          }
        }
        if (res.ok && action === "suggest_tags" && res.suggestions) {
          renderTagSuggestions(res.suggestions);
        }
      } catch (_) {
        window.AppUI?.showToast?.("AI request failed", "Error");
      }
    });
  }

  // Mount Summernote editor on the body field.
  function mountEditor() {
    const field = doc.querySelector("textarea[name='body']");
    if (!field || !window.jQuery) return;
    const $field = window.jQuery(field);
    if ($field.data("summernote")) return;
    const sanitizeHtml = (html) => {
      const div = doc.createElement("div");
      div.innerHTML = html || "";
      // Strip script/style and inline handlers
      div.querySelectorAll("script,style").forEach((n) => n.remove());
      div.querySelectorAll("*").forEach((el) => {
        Array.from(el.attributes).forEach((attr) => {
          if (attr.name && attr.name.toLowerCase().startsWith("on")) {
            el.removeAttribute(attr.name);
          }
        });
      });
      return div.innerHTML;
    };
    $field.summernote({
      placeholder: "Write your post...",
      height: 420,
      minHeight: 320,
      maxHeight: 720,
      disableDragAndDrop: true,
      shortcuts: true,
      tabDisable: false,
      dialogsInBody: true,
      codeviewFilter: true,
      codeviewIframeFilter: true,
      codemirror: false,
      toolbar: [
        ["font", ["bold", "italic", "underline", "strikethrough", "clear"]],
        ["fontname", ["fontname"]],
        ["fontsize", ["fontsize"]],
        ["color", ["color"]],
        ["para", ["ul", "ol", "paragraph", "height"]],
        ["insert", ["link", "picture", "video", "table", "hr"]],
        ["view", ["codeview", "fullscreen", "help"]],
      ],
      // Remove the default "Normal (p)" entry to avoid the unwanted (p) style selector.
      styleTags: ["blockquote", "h1", "h2", "h3", "h4", "pre"],
      fontNames: ["Inter", "Arial", "Georgia", "Roboto", "Tahoma", "Times New Roman", "Courier New", "Verdana"],
      fontSizes: ["10", "12", "14", "16", "18", "20", "24", "28"],
      lineHeights: ["0.8", "1.0", "1.2", "1.4", "1.6", "2.0"],
      callbacks: {
        onInit: function () {
          // Ensure clean, unstyled output by stripping style/class attributes.
          const html = getBodyContent();
          if (html) {
            $field.summernote("code", sanitizeHtml(html));
          }
        },
        onChange: function (contents) {
          field.value = contents;
        },
        onPaste: function (e) {
          e.preventDefault();
          const clipboard = (e.originalEvent || e).clipboardData;
          const html = clipboard?.getData("text/html");
          const text = clipboard?.getData("text/plain");
          const clean = sanitizeHtml(html || text || "");
          $field.summernote("pasteHTML", clean);
        },
        onImageUpload: function () {
          // Prevent uploads; encourage external hosting/CDN
          window.AppUI?.showToast?.("Image uploads are disabled. Use hosted image URLs.", "Info");
        },
        onChangeCodeview: function () {
          // Keep textarea in sync after code edits
          field.value = getBodyContent();
        },
      },
      popover: {
        image: [],
        link: [["link", ["linkDialogShow", "unlink"]]],
        table: [
          ["add", ["addRowDown", "addRowUp", "addColLeft", "addColRight"]],
          ["delete", ["deleteRow", "deleteCol", "deleteTable"]],
        ],
        air: [],
      },
    });
  }

  function getBodyContent() {
    const field = doc.querySelector("textarea[name='body']");
    if (!field) return "";
    if (window.jQuery) {
      const $field = window.jQuery(field);
      if ($field.data("summernote")) {
        return $field.summernote("code");
      }
    }
    return field.value || "";
  }

  function setBodyContent(html) {
    const field = doc.querySelector("textarea[name='body']");
    if (!field) return;
    if (window.jQuery) {
      const $field = window.jQuery(field);
      if ($field.data("summernote")) {
        $field.summernote("code", html);
        return;
      }
    }
    field.value = html;
  }

  function renderTagSuggestions(suggestions) {
    const box = doc.getElementById("tag-suggestions");
    const select = doc.querySelector("select[name='tags']");
    if (!box || !select) return;
    box.innerHTML = "";
    if (!suggestions.length) {
      box.innerHTML = '<span class="text-slate-500">No tag suggestions.</span>';
      return;
    }
    suggestions.forEach((s) => {
      const chip = doc.createElement("button");
      chip.type = "button";
      chip.className =
        "inline-flex items-center gap-2 px-2 py-1 rounded-full border text-xs " +
        (s.exists ? "border-emerald-200 text-emerald-700 bg-emerald-50" : "border-slate-200 text-slate-700");
      const nameSpan = document.createElement("span");
      nameSpan.textContent = s.name;
      const badge = document.createElement("span");
      badge.className = "text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-white";
      badge.textContent = s.is_curated ? "Curated" : "AI";
      chip.appendChild(nameSpan);
      chip.appendChild(badge);
      chip.addEventListener("click", () => {
        const exists = Array.from(select.options).some((o) => o.value === (s.slug || s.name) || o.text === s.name);
        if (!exists) {
          const opt = new Option(s.name, s.slug || s.name);
          opt.selected = true;
          select.add(opt);
        } else {
          Array.from(select.options).forEach((o) => {
            if (o.value === (s.slug || s.name) || o.text === s.name) o.selected = true;
          });
        }
      });
      box.appendChild(chip);
    });
  }

  function requestTagSuggestions() {
    const title = (doc.getElementById("id_title") || {}).value || "";
    const summary = (doc.getElementById("id_summary") || {}).value || "";
    const body = getBodyContent();
    const text = [title, summary, body].join(" ").trim();
    if (!text) return;
    const payload = new FormData();
    payload.append("text", text);
    fetchJson("/tags/suggest/", {
      method: "POST",
      headers: { "X-CSRFToken": getCsrf() },
      body: payload,
    })
      .then((res) => {
        if (res && res.suggestions) {
          renderTagSuggestions(res.suggestions);
        }
      })
      .catch(() => {});
  }

  function bindSlugify() {
    // no-op: slug is handled server-side; UI control removed
  }

  function bindSimilarLookup() {
    const titleField = doc.getElementById("id_title");
    const box = document.createElement("div");
    box.className = "mt-1 text-xs text-slate-600";
    if (titleField && titleField.parentNode) {
      titleField.parentNode.appendChild(box);
    }
    let timer;
    const lookup = () => {
      clearTimeout(timer);
      const q = (titleField.value || "").trim();
      if (q.length < 4) {
        box.textContent = "";
        return;
      }
      timer = setTimeout(async () => {
        try {
          const data = await fetchJson(`/blog/api/similar/?q=${encodeURIComponent(q)}`);
          if (!data.items || !data.items.length) {
            box.textContent = "No similar posts found.";
            return;
          }
          box.innerHTML = "Similar: " + data.items.map((p) => p.title).slice(0, 3).join(" • ");
        } catch (_) {
          box.textContent = "";
        }
      }, 400);
    };
    if (titleField) {
      titleField.addEventListener("input", lookup);
    }
  }

  function init() {
    try {
      loadComments();
      bindCommentForm();
      bindAutosave();
      bindTagAutocomplete();
      bindAIButtons();
      bindSlugify();
      bindSimilarLookup();
      requestTagSuggestions();
      bindCommentControls();
      mountEditor();
    } catch (err) {
      console.warn("blog.js init error", err);
    }
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();


