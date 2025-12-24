/**
 * =============================================================================
 * BROWSER COMPATIBILITY & AUTO-DETECTION SYSTEM
 * =============================================================================
 * 
 * Automatically detects browser capabilities and adjusts CSS/JS accordingly
 * Progressive enhancement with graceful degradation
 * 
 * Version: 1.0.0
 * Date: 2025-12-22
 * 
 * =============================================================================
 */

'use strict';

const BrowserCompat = {
  // Browser detection
  browser: {
    name: 'Unknown',
    version: 0,
    engine: 'Unknown',
    os: 'Unknown',
    isMobile: false,
    isTablet: false,
  },

  // Feature detection
  features: {
    css: {
      grid: false,
      flexbox: false,
      backdrop: false,
      customProperties: false,
      supports: false,
    },
    js: {
      fetch: false,
      promise: false,
      async: false,
      proxy: false,
      symbol: false,
      weakMap: false,
      intersectionObserver: false,
      mutationObserver: false,
      resizeObserver: false,
      serviceWorker: false,
      localStorage: false,
      indexedDB: false,
    },
    dom: {
      classList: false,
      dataset: false,
      querySelector: false,
      template: false,
      shadow: false,
    },
    media: {
      webp: false,
      webm: false,
      h264: false,
      opus: false,
    },
  },

  // Polyfills & fallbacks
  polyfills: {},

  /**
   * Initialize browser detection and feature detection
   */
  init() {
    this.detectBrowser();
    this.detectFeatures();
    this.applyPolyfills();
    this.adjustDOM();
    this.logCapabilities();
  },

  /**
   * Detect browser and OS
   */
  detectBrowser() {
    const ua = navigator.userAgent;
    const uaLower = ua.toLowerCase();

    // Browser detection
    if (uaLower.includes('edg/')) {
      this.browser.name = 'Edge';
      this.browser.version = parseInt(ua.match(/edg\/(\d+)/)?.[1] || 0);
      this.browser.engine = 'Chromium';
    } else if (uaLower.includes('chrome')) {
      this.browser.name = 'Chrome';
      this.browser.version = parseInt(ua.match(/chrome\/(\d+)/)?.[1] || 0);
      this.browser.engine = 'Chromium';
    } else if (uaLower.includes('firefox')) {
      this.browser.name = 'Firefox';
      this.browser.version = parseInt(ua.match(/firefox\/(\d+)/)?.[1] || 0);
      this.browser.engine = 'Gecko';
    } else if (uaLower.includes('safari') && !uaLower.includes('chrome')) {
      this.browser.name = 'Safari';
      this.browser.version = parseInt(ua.match(/version\/(\d+)/)?.[1] || 0);
      this.browser.engine = 'WebKit';
    } else if (uaLower.includes('trident') || uaLower.includes('msie')) {
      this.browser.name = 'IE';
      this.browser.version = parseInt(ua.match(/(?:msie |rv:)(\d+)/)?.[1] || 0);
      this.browser.engine = 'Trident';
    }

    // OS detection
    if (uaLower.includes('windows')) {
      this.browser.os = 'Windows';
    } else if (uaLower.includes('mac')) {
      this.browser.os = 'macOS';
    } else if (uaLower.includes('android')) {
      this.browser.os = 'Android';
      this.browser.isMobile = true;
    } else if (uaLower.includes('iphone') || uaLower.includes('ios')) {
      this.browser.os = 'iOS';
      this.browser.isMobile = true;
    } else if (uaLower.includes('ipad')) {
      this.browser.os = 'iPadOS';
      this.browser.isTablet = true;
    } else if (uaLower.includes('linux')) {
      this.browser.os = 'Linux';
    }

    // Add browser class to HTML
    document.documentElement.classList.add(
      `browser-${this.browser.name.toLowerCase()}`,
      `os-${this.browser.os.toLowerCase().replace(/\s+/g, '-')}`,
      this.browser.isMobile ? 'is-mobile' : 'is-desktop',
      this.browser.isTablet ? 'is-tablet' : ''
    );
  },

  /**
   * Detect supported features
   */
  detectFeatures() {
    // CSS features
    this.features.css.grid = CSS.supports('display', 'grid');
    this.features.css.flexbox = CSS.supports('display', 'flex');
    this.features.css.backdrop = CSS.supports('backdrop-filter', 'blur(1px)') || 
                                  CSS.supports('-webkit-backdrop-filter', 'blur(1px)');
    this.features.css.customProperties = CSS.supports('--test', '0');
    this.features.css.supports = typeof CSS !== 'undefined' && typeof CSS.supports === 'function';

    // JavaScript features
    this.features.js.fetch = typeof fetch !== 'undefined';
    this.features.js.promise = typeof Promise !== 'undefined';
    this.features.js.async = (async () => {})().constructor.name === 'AsyncFunction';
    this.features.js.proxy = typeof Proxy !== 'undefined';
    this.features.js.symbol = typeof Symbol !== 'undefined';
    this.features.js.weakMap = typeof WeakMap !== 'undefined';
    this.features.js.intersectionObserver = typeof IntersectionObserver !== 'undefined';
    this.features.js.mutationObserver = typeof MutationObserver !== 'undefined';
    this.features.js.resizeObserver = typeof ResizeObserver !== 'undefined';
    this.features.js.serviceWorker = 'serviceWorker' in navigator;
    this.features.js.localStorage = this.testLocalStorage();
    this.features.js.indexedDB = typeof indexedDB !== 'undefined';

    // DOM features
    this.features.dom.classList = 'classList' in document.documentElement;
    this.features.dom.dataset = 'dataset' in document.documentElement;
    this.features.dom.querySelector = typeof document.querySelector === 'function';
    this.features.dom.template = 'content' in document.createElement('template');
    this.features.dom.shadow = 'attachShadow' in Element.prototype;

    // Media features
    this.features.media.webp = this.testImageFormat('webp');
    this.features.media.webm = this.testVideoFormat('webm');
    this.features.media.h264 = this.testVideoFormat('h264');
    this.features.media.opus = this.testAudioFormat('opus');

    // Add feature classes to HTML
    Object.entries(this.features).forEach(([category, features]) => {
      Object.entries(features).forEach(([feature, supported]) => {
        if (supported) {
          document.documentElement.classList.add(`supports-${category}-${feature}`);
        }
      });
    });
  },

  /**
   * Test if localStorage is available
   */
  testLocalStorage() {
    try {
      const test = '__test__';
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  },

  /**
   * Test image format support
   */
  testImageFormat(format) {
    const canvas = document.createElement('canvas');
    return canvas.toDataURL(`image/${format}`).indexOf(`image/${format}`) === 5;
  },

  /**
   * Test video format support
   */
  testVideoFormat(format) {
    const video = document.createElement('video');
    return video.canPlayType(`video/${format}`) !== '';
  },

  /**
   * Test audio format support
   */
  testAudioFormat(format) {
    const audio = document.createElement('audio');
    return audio.canPlayType(`audio/${format}`) !== '';
  },

  /**
   * Apply polyfills for missing features
   */
  applyPolyfills() {
    // Polyfill for older browsers
    if (!this.features.js.fetch) {
      this.polyfills.fetch = this.createFetchPolyfill();
    }

    if (!this.features.js.promise) {
      this.polyfills.promise = this.createPromisePolyfill();
    }

    if (!this.features.dom.classList) {
      this.polyfills.classList = this.createClassListPolyfill();
    }
  },

  /**
   * Adjust DOM based on capabilities
   */
  adjustDOM() {
    // Hide unsupported features
    if (!this.features.css.grid) {
      document.documentElement.classList.add('no-grid');
    }

    if (!this.features.js.intersectionObserver) {
      document.documentElement.classList.add('no-intersection-observer');
    }

    // Load appropriate stylesheets
    if (this.browser.isMobile) {
      this.loadStylesheet('/static/css/mobile.css');
    }

    if (this.browser.name === 'IE') {
      this.loadStylesheet('/static/css/ie-fixes.css');
    }
  },

  /**
   * Load stylesheet dynamically
   */
  loadStylesheet(href) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
  },

  /**
   * Log capabilities for debugging
   */
  logCapabilities() {
    if (window.DEBUG) {
      console.log('[BrowserCompat] Browser:', this.browser);
      console.log('[BrowserCompat] Features:', this.features);
    }
  },

  /**
   * Check if feature is supported
   */
  supports(category, feature) {
    return this.features[category]?.[feature] ?? false;
  },

  /**
   * Get browser info
   */
  getBrowser() {
    return this.browser;
  },

  /**
   * Create fetch polyfill
   */
  createFetchPolyfill() {
    return function(url, options) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(options?.method || 'GET', url);
        
        if (options?.headers) {
          Object.entries(options.headers).forEach(([key, value]) => {
            xhr.setRequestHeader(key, value);
          });
        }

        xhr.onload = () => {
          resolve({
            ok: xhr.status >= 200 && xhr.status < 300,
            status: xhr.status,
            text: () => Promise.resolve(xhr.responseText),
            json: () => Promise.resolve(JSON.parse(xhr.responseText)),
          });
        };

        xhr.onerror = () => reject(new Error('Network error'));
        xhr.send(options?.body);
      });
    };
  },

  /**
   * Create Promise polyfill (simplified)
   */
  createPromisePolyfill() {
    return function(executor) {
      let state = 'pending';
      let value;
      const handlers = [];

      const resolve = (v) => {
        if (state !== 'pending') return;
        state = 'fulfilled';
        value = v;
        handlers.forEach(h => h());
      };

      const reject = (e) => {
        if (state !== 'pending') return;
        state = 'rejected';
        value = e;
        handlers.forEach(h => h());
      };

      executor(resolve, reject);

      return {
        then: (onFulfilled, onRejected) => {
          handlers.push(() => {
            if (state === 'fulfilled') onFulfilled?.(value);
            if (state === 'rejected') onRejected?.(value);
          });
        },
      };
    };
  },

  /**
   * Create classList polyfill
   */
  createClassListPolyfill() {
    return {
      add: (el, className) => {
        el.className = (el.className + ' ' + className).trim();
      },
      remove: (el, className) => {
        el.className = el.className.replace(className, '').trim();
      },
      toggle: (el, className) => {
        if (el.className.includes(className)) {
          this.remove(el, className);
        } else {
          this.add(el, className);
        }
      },
    };
  },
};

// Initialize on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => BrowserCompat.init());
} else {
  BrowserCompat.init();
}

// Export to window
window.BrowserCompat = BrowserCompat;

