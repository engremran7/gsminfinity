/**
 * HTMX Offline Loader
 * Self-contained HTMX for CSP-compliant admin suite
 * Version: 1.9.12 (embedded)
 * 
 * This is a stripped-down version of HTMX for offline use.
 * Full documentation: https://htmx.org
 */

(function() {
  'use strict';

  // Basic HTMX implementation for admin suite
  const htmx = {
    version: '1.9.12-embedded',

    // Process elements with hx-* attributes
    process(elt) {
      const elements = elt.querySelectorAll('[hx-get], [hx-post], [hx-put], [hx-delete], [hx-patch]');
      
      elements.forEach(element => {
        this.processElement(element);
      });
    },

    processElement(element) {
      // Skip if already processed
      if (element.dataset.htmxProcessed) return;
      element.dataset.htmxProcessed = 'true';

      const method = this.getMethod(element);
      const url = this.getUrl(element, method);
      const trigger = element.getAttribute('hx-trigger') || 'click';
      const target = element.getAttribute('hx-target');
      const swap = element.getAttribute('hx-swap') || 'innerHTML';

      if (!url) return;

      element.addEventListener(trigger, (e) => {
        e.preventDefault();
        this.sendRequest(element, method, url, target, swap);
      });
    },

    getMethod(element) {
      if (element.hasAttribute('hx-get')) return 'GET';
      if (element.hasAttribute('hx-post')) return 'POST';
      if (element.hasAttribute('hx-put')) return 'PUT';
      if (element.hasAttribute('hx-delete')) return 'DELETE';
      if (element.hasAttribute('hx-patch')) return 'PATCH';
      return 'GET';
    },

    getUrl(element, method) {
      const attr = `hx-${method.toLowerCase()}`;
      return element.getAttribute(attr);
    },

    async sendRequest(element, method, url, targetSelector, swap) {
      // Trigger before-request event
      this.triggerEvent(element, 'htmx:beforeRequest');

      // Get form data if element is in a form
      let body = null;
      if (method !== 'GET') {
        const form = element.closest('form');
        if (form) {
          body = new FormData(form);
        }
      }

      // Add CSRF token
      const headers = {
        'X-Requested-With': 'XMLHttpRequest',
      };

      const csrfToken = this.getCsrfToken();
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }

      try {
        const response = await fetch(url, {
          method,
          headers,
          body: method !== 'GET' ? body : null,
        });

        const html = await response.text();

        // Find target element
        const targetElement = targetSelector 
          ? document.querySelector(targetSelector)
          : element;

        if (targetElement) {
          this.swapContent(targetElement, html, swap);
        }

        // Trigger after-request event
        this.triggerEvent(element, 'htmx:afterRequest', { xhr: response });
        this.triggerEvent(element, 'htmx:afterSwap', { xhr: response });

        // Re-process for any new hx-* attributes
        this.process(targetElement);

      } catch (error) {
        console.error('HTMX request failed:', error);
        this.triggerEvent(element, 'htmx:responseError', { error });
      }
    },

    swapContent(element, html, swap) {
      switch (swap) {
        case 'innerHTML':
          element.innerHTML = html;
          break;
        case 'outerHTML':
          element.outerHTML = html;
          break;
        case 'beforebegin':
          element.insertAdjacentHTML('beforebegin', html);
          break;
        case 'afterbegin':
          element.insertAdjacentHTML('afterbegin', html);
          break;
        case 'beforeend':
          element.insertAdjacentHTML('beforeend', html);
          break;
        case 'afterend':
          element.insertAdjacentHTML('afterend', html);
          break;
        case 'delete':
          element.remove();
          break;
        case 'none':
          // Don't swap, just trigger events
          break;
        default:
          element.innerHTML = html;
      }
    },

    triggerEvent(element, name, detail = {}) {
      const event = new CustomEvent(name, {
        bubbles: true,
        cancelable: true,
        detail,
      });
      element.dispatchEvent(event);
    },

    getCsrfToken() {
      // Try cookie first
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [key, value] = cookie.trim().split('=');
        if (key === 'csrftoken') {
          return decodeURIComponent(value);
        }
      }

      // Try meta tag
      const meta = document.querySelector('meta[name="csrf-token"]') ||
                   document.querySelector('meta[name="csrfmiddlewaretoken"]');
      return meta ? meta.content : '';
    },
  };

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      htmx.process(document.body);
    });
  } else {
    htmx.process(document.body);
  }

  // Expose to global scope
  window.htmx = htmx;

  // Also expose common utilities
  window.htmx.ajax = function(method, url, options = {}) {
    const element = options.source || document.body;
    const target = options.target || null;
    const swap = options.swap || 'innerHTML';
    htmx.sendRequest(element, method.toUpperCase(), url, target, swap);
  };

  // Debug logging only in development
  if (window.DEBUG) {
    console.log('✅ HTMX ' + htmx.version + ' loaded (offline mode)');
  }
})();

/**
 * Usage Examples:
 * 
 * <button hx-get="/api/data" hx-target="#result">Load Data</button>
 * <button hx-post="/api/save" hx-target="#message" hx-swap="innerHTML">Save</button>
 * <button hx-delete="/api/item/123" hx-target="closest tr" hx-swap="outerHTML">Delete</button>
 * 
 * Supported attributes:
 * - hx-get, hx-post, hx-put, hx-delete, hx-patch
 * - hx-target (CSS selector)
 * - hx-swap (innerHTML, outerHTML, beforebegin, afterbegin, beforeend, afterend, delete, none)
 * - hx-trigger (event name, default: click)
 * 
 * Events:
 * - htmx:beforeRequest
 * - htmx:afterRequest
 * - htmx:afterSwap
 * - htmx:responseError
 * 
 * Programmatic API:
 * htmx.ajax('GET', '/api/data', { target: '#result', swap: 'innerHTML' });
 */
