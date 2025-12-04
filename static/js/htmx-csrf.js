// Normalized CSRF extraction for HTMX requests.
// Hardened for null-safety and explicit error reporting.

function getCsrfToken() {
  const tag =
    document.querySelector('meta[name="csrf-token"]') ||
    document.querySelector('meta[name="csrfmiddlewaretoken"]') ||
    document.querySelector('meta[name="X-CSRFToken"]');
  if (!tag) {
    console.error("HTMX-CSRF: Missing <meta name='csrf-token'>");
    return "";
  }
  return tag.getAttribute("content") || "";
}

if (window.htmx && typeof window.htmx.on === "function") {
  window.htmx.on("configRequest.htmx", (event) => {
    try {
      const token = getCsrfToken();
      if (token) {
        event.detail.headers["X-CSRFToken"] = token;
        event.detail.headers["X-Requested-With"] =
          event.detail.headers["X-Requested-With"] || "XMLHttpRequest";
      }
    } catch (err) {
      console.error("HTMX-CSRF attach failed:", err);
    }
  });
}
