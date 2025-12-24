/* Shared HTMX Configuration */
/* HTMX is used in both admin and enduser interfaces */

if (typeof htmx !== 'undefined') {
  // Configure HTMX defaults
  htmx.config.timeout = 10000;
  htmx.config.defaultIndicatorStyle = 'spinner';
  
  // Ensure CSRF token is included in HTMX requests
  document.addEventListener('htmx:configRequest', function(event) {
    const csrfToken = window.APP?.getCsrfToken?.();
    if (csrfToken) {
      event.detail.headers['X-CSRFToken'] = csrfToken;
    }
  });
  
  window.HTMX_INITIALIZED = true;
}
