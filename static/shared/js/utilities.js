/* ============================================================================
   GsmInfinity - Shared JavaScript Utilities
   Enterprise Edition
   Available to both admin and enduser frontends
   ============================================================================ */

if (!window.APP) {
  window.APP = {};
}

/* ============================================================================
   CSRF Token Management
   ============================================================================ */

/**
 * Get CSRF token from meta tag, input field, or cookie
 * @returns {string|null} The CSRF token or null if not found
 */
window.APP.getCsrfToken = function() {
  // Try meta tag first (recommended)
  const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  if (metaToken) return metaToken;
  
  // Try hidden input field
  const inputToken = document.querySelector('[name="csrfmiddlewaretoken"]');
  if (inputToken) return inputToken.value;
  
  // Fall back to cookie
  const name = 'csrftoken';
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
  }
  return null;
};

/* ============================================================================
   Enhanced Fetch API
   ============================================================================ */

/**
 * Fetch wrapper with CSRF token and error handling
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise} Fetch promise
 */
window.APP.fetch = function(url, options = {}) {
  const csrfToken = window.APP.getCsrfToken();
  const headers = { ...options.headers };
  
  // Add CSRF token for non-GET requests
  if (options.method && options.method.toUpperCase() !== 'GET' && csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  }
  
  // Add JSON content type if body is object
  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }
  
  return fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers
  });
};

/**
 * JSON fetch helper with automatic response parsing
 * @param {string} url - The URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Object>} Parsed JSON response
 */
window.APP.fetchJSON = async function(url, options = {}) {
  const response = await window.APP.fetch(url, {
    ...options,
    headers: {
      'Accept': 'application/json',
      ...options.headers
    }
  });
  
  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
    error.status = response.status;
    error.response = response;
    throw error;
  }
  
  return response.json();
};

/* ============================================================================
   Utility Functions
   ============================================================================ */

/**
 * Debug logging (only in development)
 * @param {string} message - Log message
 * @param {*} data - Optional data to log
 */
window.APP.log = function(message, data = null) {
  if (window.DEBUG) {
    console.log(`[APP] ${message}`, data || '');
  }
};

/**
 * Debounce function - limits how often a function can fire
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
window.APP.debounce = function(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func.apply(this, args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Throttle function - ensures function is called at most once per interval
 * @param {Function} func - Function to throttle
 * @param {number} limit - Minimum time between calls in milliseconds
 * @returns {Function} Throttled function
 */
window.APP.throttle = function(func, limit = 100) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

/**
 * Format a date for display
 * @param {Date|string|number} date - Date to format
 * @param {string} format - Format type: 'short', 'long', 'relative', 'iso'
 * @returns {string} Formatted date string
 */
window.APP.formatDate = function(date, format = 'short') {
  const d = new Date(date);
  if (isNaN(d.getTime())) return '';
  
  switch (format) {
    case 'short':
      return d.toLocaleDateString();
    case 'long':
      return d.toLocaleString();
    case 'iso':
      return d.toISOString();
    case 'relative':
      return window.APP.getRelativeTime(d);
    default:
      return d.toString();
  }
};

/**
 * Get relative time string (e.g., "2 hours ago")
 * @param {Date} date - Date to format
 * @returns {string} Relative time string
 */
window.APP.getRelativeTime = function(date) {
  const now = new Date();
  const diff = now - new Date(date);
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  
  if (seconds < 60) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return window.APP.formatDate(date, 'short');
};

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
window.APP.escapeHtml = function(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
window.APP.copyToClipboard = async function(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    // Fallback for older browsers
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
    return true;
  } catch (err) {
    window.APP.log('Copy to clipboard failed', err);
    return false;
  }
};

/**
 * Generate a unique ID
 * @param {string} prefix - Optional prefix for the ID
 * @returns {string} Unique ID
 */
window.APP.uniqueId = function(prefix = 'id') {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).substr(2, 9)}`;
};

/**
 * Check if element is in viewport
 * @param {Element} el - Element to check
 * @returns {boolean} Whether element is visible
 */
window.APP.isInViewport = function(el) {
  const rect = el.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
};

/* ============================================================================
   Event Helpers
   ============================================================================ */

/**
 * Dispatch a custom event
 * @param {string} name - Event name
 * @param {Object} detail - Event detail data
 * @param {Element} target - Target element (defaults to document)
 */
window.APP.emit = function(name, detail = {}, target = document) {
  const event = new CustomEvent(name, {
    bubbles: true,
    cancelable: true,
    detail
  });
  target.dispatchEvent(event);
};

/**
 * Listen for a custom event
 * @param {string} name - Event name
 * @param {Function} handler - Event handler
 * @param {Element} target - Target element (defaults to document)
 * @returns {Function} Function to remove listener
 */
window.APP.on = function(name, handler, target = document) {
  target.addEventListener(name, handler);
  return () => target.removeEventListener(name, handler);
};

/* ============================================================================
   Storage Helpers
   ============================================================================ */

/**
 * Safe localStorage get with JSON parsing
 * @param {string} key - Storage key
 * @param {*} defaultValue - Default value if key doesn't exist
 * @returns {*} Stored value or default
 */
window.APP.storage = {
  get: function(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (e) {
      return defaultValue;
    }
  },
  
  set: function(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      return false;
    }
  },
  
  remove: function(key) {
    try {
      localStorage.removeItem(key);
      return true;
    } catch (e) {
      return false;
    }
  }
};

/* ============================================================================
   Initialization
   ============================================================================ */

/**
 * Initialize shared utilities
 */
window.APP.init = function() {
  window.APP.log('APP utilities initialized v2.0');
};

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', window.APP.init);
} else {
  window.APP.init();
}
