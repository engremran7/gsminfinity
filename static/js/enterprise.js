/**
 * GSM Infinity - Enterprise JavaScript
 * 
 * 100% CSP-compliant JavaScript for all UI interactions.
 * No inline scripts, no eval(), pure event-driven architecture.
 * 
 * Features:
 * - Modal management
 * - Dropdown menus
 * - Toast notifications
 * - Form validation
 * - Theme switcher
 * - Mobile navigation
 * - Tabs
 * - Tooltips
 * - Character counter
 * - File upload
 * - Password strength
 * - Search with debounce
 * - Infinite scroll
 * - Lazy loading
 */

(function() {
  'use strict';

  // ========================================================================
  // UTILITIES
  // ========================================================================

  const Utils = {
    // Debounce function
    debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
        const later = () => {
          clearTimeout(timeout);
          func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
      };
    },

    // Throttle function
    throttle(func, limit) {
      let inThrottle;
      return function(...args) {
        if (!inThrottle) {
          func.apply(this, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      };
    },

    // Generate unique ID
    generateId() {
      return `id_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    // Get transition duration from element
    getTransitionDuration(element) {
      const duration = window.getComputedStyle(element).transitionDuration;
      return parseFloat(duration) * 1000;
    },

    // Trap focus within element
    trapFocus(element) {
      const focusableElements = element.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      element.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
          if (e.shiftKey && document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      });

      firstElement.focus();
    }
  };

  // ========================================================================
  // MODAL MANAGEMENT
  // ========================================================================

  class Modal {
    constructor(modalElement) {
      this.modal = modalElement;
      this.backdrop = document.querySelector('.modal-backdrop');
      this.isOpen = false;
      this.init();
    }

    init() {
      // Close button
      const closeBtn = this.modal.querySelector('.modal-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => this.close());
      }

      // Backdrop click
      if (this.backdrop) {
        this.backdrop.addEventListener('click', () => this.close());
      }

      // Escape key
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });
    }

    open() {
      this.isOpen = true;
      this.modal.classList.add('active');
      if (this.backdrop) {
        this.backdrop.classList.add('active');
      }
      document.body.style.overflow = 'hidden';
      Utils.trapFocus(this.modal);
      this.modal.dispatchEvent(new CustomEvent('modal:opened'));
    }

    close() {
      this.isOpen = false;
      this.modal.classList.remove('active');
      if (this.backdrop) {
        this.backdrop.classList.remove('active');
      }
      document.body.style.overflow = '';
      this.modal.dispatchEvent(new CustomEvent('modal:closed'));
    }

    toggle() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    }
  }

  // Initialize modals
  const modals = new Map();
  document.querySelectorAll('[data-modal-trigger]').forEach(trigger => {
    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      const modalId = trigger.dataset.modalTrigger;
      const modalElement = document.getElementById(modalId);
      
      if (modalElement) {
        if (!modals.has(modalId)) {
          modals.set(modalId, new Modal(modalElement));
        }
        modals.get(modalId).open();
      }
    });
  });

  // ========================================================================
  // DROPDOWN MENUS
  // ========================================================================

  class Dropdown {
    constructor(dropdownElement) {
      this.dropdown = dropdownElement;
      this.toggle = this.dropdown.querySelector('[data-dropdown-toggle]');
      this.menu = this.dropdown.querySelector('.dropdown-menu');
      this.isOpen = false;
      this.init();
    }

    init() {
      this.toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleMenu();
      });

      // Close on outside click
      document.addEventListener('click', (e) => {
        if (!this.dropdown.contains(e.target) && this.isOpen) {
          this.close();
        }
      });

      // Close on escape
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });

      // Keyboard navigation
      this.menu.querySelectorAll('.dropdown-item').forEach((item, index, items) => {
        item.addEventListener('keydown', (e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault();
            const nextIndex = (index + 1) % items.length;
            items[nextIndex].focus();
          } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            const prevIndex = (index - 1 + items.length) % items.length;
            items[prevIndex].focus();
          }
        });
      });
    }

    toggleMenu() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    }

    open() {
      this.isOpen = true;
      this.menu.classList.add('active');
      this.toggle.setAttribute('aria-expanded', 'true');
      this.menu.querySelector('.dropdown-item')?.focus();
    }

    close() {
      this.isOpen = false;
      this.menu.classList.remove('active');
      this.toggle.setAttribute('aria-expanded', 'false');
      this.toggle.focus();
    }
  }

  // Initialize dropdowns
  document.querySelectorAll('.dropdown').forEach(dropdown => {
    new Dropdown(dropdown);
  });

  // ========================================================================
  // TOAST NOTIFICATIONS
  // ========================================================================

  const ToastManager = {
    container: null,
    toasts: [],

    init() {
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.className = 'toast-container toast-container-top-right';
        document.body.appendChild(this.container);
      }
    },

    show(options = {}) {
      this.init();

      const toast = document.createElement('div');
      toast.className = `toast ${options.type ? 'toast-' + options.type : ''}`;
      toast.innerHTML = `
        ${options.icon ? `<span class="toast-icon">${options.icon}</span>` : ''}
        <div class="toast-content">
          ${options.title ? `<div class="toast-title">${options.title}</div>` : ''}
          ${options.message ? `<div class="toast-description">${options.message}</div>` : ''}
        </div>
        <button class="toast-close" aria-label="Close">×</button>
      `;

      const closeBtn = toast.querySelector('.toast-close');
      closeBtn.addEventListener('click', () => this.remove(toast));

      this.container.appendChild(toast);
      this.toasts.push(toast);

      // Auto remove
      const duration = options.duration || 5000;
      if (duration > 0) {
        setTimeout(() => this.remove(toast), duration);
      }

      return toast;
    },

    remove(toast) {
      toast.style.animation = 'slideOut 0.3s ease-out';
      setTimeout(() => {
        if (toast.parentElement) {
          toast.parentElement.removeChild(toast);
        }
        this.toasts = this.toasts.filter(t => t !== toast);
      }, 300);
    },

    success(message, title = 'Success') {
      return this.show({ type: 'success', title, message });
    },

    error(message, title = 'Error') {
      return this.show({ type: 'error', title, message });
    },

    warning(message, title = 'Warning') {
      return this.show({ type: 'warning', title, message });
    },

    info(message, title = 'Info') {
      return this.show({ type: 'info', title, message });
    }
  };

  // Expose globally
  window.Toast = ToastManager;

  // ========================================================================
  // FORM VALIDATION
  // ========================================================================

  class FormValidator {
    constructor(formElement) {
      this.form = formElement;
      this.init();
    }

    init() {
      this.form.addEventListener('submit', (e) => {
        if (!this.validate()) {
          e.preventDefault();
        }
      });

      // Real-time validation
      this.form.querySelectorAll('input, textarea, select').forEach(field => {
        field.addEventListener('blur', () => this.validateField(field));
        field.addEventListener('input', () => {
          if (field.classList.contains('is-invalid')) {
            this.validateField(field);
          }
        });
      });
    }

    validate() {
      let isValid = true;
      this.form.querySelectorAll('[required], [pattern], [minlength], [maxlength]').forEach(field => {
        if (!this.validateField(field)) {
          isValid = false;
        }
      });
      return isValid;
    }

    validateField(field) {
      const value = field.value.trim();
      let isValid = true;
      let errorMessage = '';

      // Required check
      if (field.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'This field is required.';
      }

      // Pattern check
      if (isValid && field.hasAttribute('pattern')) {
        const pattern = new RegExp(field.getAttribute('pattern'));
        if (!pattern.test(value)) {
          isValid = false;
          errorMessage = field.getAttribute('data-pattern-error') || 'Invalid format.';
        }
      }

      // Email check
      if (isValid && field.type === 'email') {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailPattern.test(value)) {
          isValid = false;
          errorMessage = 'Please enter a valid email address.';
        }
      }

      // Min length check
      if (isValid && field.hasAttribute('minlength')) {
        const minLength = parseInt(field.getAttribute('minlength'));
        if (value.length < minLength) {
          isValid = false;
          errorMessage = `Minimum ${minLength} characters required.`;
        }
      }

      // Max length check
      if (isValid && field.hasAttribute('maxlength')) {
        const maxLength = parseInt(field.getAttribute('maxlength'));
        if (value.length > maxLength) {
          isValid = false;
          errorMessage = `Maximum ${maxLength} characters allowed.`;
        }
      }

      // Update UI
      if (isValid) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        this.removeError(field);
      } else {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        this.showError(field, errorMessage);
      }

      return isValid;
    }

    showError(field, message) {
      this.removeError(field);
      const error = document.createElement('span');
      error.className = 'form-error';
      error.textContent = message;
      error.setAttribute('role', 'alert');
      field.parentElement.appendChild(error);
    }

    removeError(field) {
      const error = field.parentElement.querySelector('.form-error');
      if (error) {
        error.remove();
      }
    }
  }

  // Initialize form validation
  document.querySelectorAll('form[data-validate]').forEach(form => {
    new FormValidator(form);
  });

  // ========================================================================
  // THEME SWITCHER
  // ========================================================================

  const ThemeManager = {
    currentTheme: localStorage.getItem('theme') || 'light',

    init() {
      this.applyTheme(this.currentTheme);
      
      document.querySelectorAll('[data-theme-toggle]').forEach(toggle => {
        toggle.addEventListener('click', () => this.toggleTheme());
      });
    },

    applyTheme(theme) {
      this.currentTheme = theme;
      document.documentElement.classList.toggle('dark', theme === 'dark');
      localStorage.setItem('theme', theme);
      
      document.querySelectorAll('[data-theme-toggle]').forEach(toggle => {
        toggle.setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`);
      });
    },

    toggleTheme() {
      this.applyTheme(this.currentTheme === 'dark' ? 'light' : 'dark');
    }
  };

  ThemeManager.init();

  // ========================================================================
  // MOBILE NAVIGATION
  // ========================================================================

  const MobileNav = {
    init() {
      const toggle = document.querySelector('.navbar-toggle');
      const menu = document.querySelector('.navbar-menu');

      if (toggle && menu) {
        toggle.addEventListener('click', () => {
          menu.classList.toggle('active');
          const isExpanded = menu.classList.contains('active');
          toggle.setAttribute('aria-expanded', isExpanded);
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
          if (!toggle.contains(e.target) && !menu.contains(e.target)) {
            menu.classList.remove('active');
            toggle.setAttribute('aria-expanded', 'false');
          }
        });
      }
    }
  };

  MobileNav.init();

  // ========================================================================
  // TABS
  // ========================================================================

  class Tabs {
    constructor(tabsElement) {
      this.tabs = tabsElement;
      this.links = this.tabs.querySelectorAll('.tabs-link');
      this.panels = document.querySelectorAll('.tabs-panel');
      this.init();
    }

    init() {
      this.links.forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          this.activate(link);
        });

        // Keyboard navigation
        link.addEventListener('keydown', (e) => {
          const index = Array.from(this.links).indexOf(link);
          if (e.key === 'ArrowRight') {
            e.preventDefault();
            const nextIndex = (index + 1) % this.links.length;
            this.links[nextIndex].click();
            this.links[nextIndex].focus();
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            const prevIndex = (index - 1 + this.links.length) % this.links.length;
            this.links[prevIndex].click();
            this.links[prevIndex].focus();
          }
        });
      });
    }

    activate(activeLink) {
      const targetId = activeLink.getAttribute('href').substring(1);

      // Update links
      this.links.forEach(link => {
        link.classList.remove('active');
        link.setAttribute('aria-selected', 'false');
        link.setAttribute('tabindex', '-1');
      });
      activeLink.classList.add('active');
      activeLink.setAttribute('aria-selected', 'true');
      activeLink.setAttribute('tabindex', '0');

      // Update panels
      this.panels.forEach(panel => {
        panel.hidden = true;
      });
      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.hidden = false;
      }
    }
  }

  // Initialize tabs
  document.querySelectorAll('.tabs').forEach(tabs => {
    new Tabs(tabs);
  });

  // ========================================================================
  // CHARACTER COUNTER
  // ========================================================================

  document.querySelectorAll('[data-character-count]').forEach(field => {
    const maxLength = parseInt(field.getAttribute('maxlength')) || parseInt(field.dataset.characterCount);
    const counter = document.createElement('span');
    counter.className = 'form-counter';
    field.parentElement.classList.add('form-group-counter');
    field.parentElement.appendChild(counter);

    const updateCounter = () => {
      const length = field.value.length;
      counter.textContent = `${length} / ${maxLength}`;
      
      counter.classList.remove('form-counter-limit', 'form-counter-exceeded');
      if (length > maxLength * 0.9) {
        counter.classList.add('form-counter-limit');
      }
      if (length > maxLength) {
        counter.classList.add('form-counter-exceeded');
      }
    };

    field.addEventListener('input', updateCounter);
    updateCounter();
  });

  // ========================================================================
  // PASSWORD STRENGTH
  // ========================================================================

  document.querySelectorAll('[data-password-strength]').forEach(field => {
    const strengthContainer = document.createElement('div');
    strengthContainer.className = 'password-strength';
    strengthContainer.innerHTML = `
      <div class="password-strength-meter">
        <div class="password-strength-bar"></div>
      </div>
      <span class="password-strength-label"></span>
    `;
    field.parentElement.appendChild(strengthContainer);

    const bar = strengthContainer.querySelector('.password-strength-bar');
    const label = strengthContainer.querySelector('.password-strength-label');

    field.addEventListener('input', () => {
      const password = field.value;
      const strength = calculatePasswordStrength(password);
      
      strengthContainer.className = 'password-strength';
      if (strength.score >= 80) {
        strengthContainer.classList.add('password-strength-strong');
        label.textContent = 'Strong password';
      } else if (strength.score >= 50) {
        strengthContainer.classList.add('password-strength-medium');
        label.textContent = 'Medium password';
      } else if (password.length > 0) {
        strengthContainer.classList.add('password-strength-weak');
        label.textContent = 'Weak password';
      }
    });
  });

  function calculatePasswordStrength(password) {
    let score = 0;
    
    if (password.length >= 8) score += 20;
    if (password.length >= 12) score += 10;
    if (/[a-z]/.test(password)) score += 20;
    if (/[A-Z]/.test(password)) score += 20;
    if (/[0-9]/.test(password)) score += 15;
    if (/[^a-zA-Z0-9]/.test(password)) score += 15;
    
    return { score };
  }

  // ========================================================================
  // SEARCH WITH DEBOUNCE
  // ========================================================================

  document.querySelectorAll('[data-search-api]').forEach(searchInput => {
    const apiUrl = searchInput.dataset.searchApi;
    const resultsContainer = document.getElementById(searchInput.dataset.searchResults);
    
    const performSearch = Utils.debounce(async (query) => {
      if (query.length < 2) {
        resultsContainer.innerHTML = '';
        return;
      }

      try {
        const response = await fetch(`${apiUrl}?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        displaySearchResults(data, resultsContainer);
      } catch (error) {
        console.error('Search error:', error);
      }
    }, 300);

    searchInput.addEventListener('input', (e) => {
      performSearch(e.target.value);
    });
  });

  function displaySearchResults(data, container) {
    if (!data.results || data.results.length === 0) {
      container.innerHTML = '<p class="text-sm text-slate-500 p-4">No results found</p>';
      return;
    }

    container.innerHTML = data.results.map(result => `
      <a href="${result.url}" class="dropdown-item">
        ${result.icon ? `<span>${result.icon}</span>` : ''}
        <span>${result.title}</span>
      </a>
    `).join('');
  }

  // ========================================================================
  // FILE UPLOAD WITH PREVIEW
  // ========================================================================

  document.querySelectorAll('[data-file-preview]').forEach(fileInput => {
    const previewContainer = document.getElementById(fileInput.dataset.filePreview);
    
    fileInput.addEventListener('change', (e) => {
      const files = Array.from(e.target.files);
      previewContainer.innerHTML = '';

      files.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
          const preview = document.createElement('div');
          preview.className = 'file-preview-item';
          
          if (file.type.startsWith('image/')) {
            preview.innerHTML = `
              <img src="${e.target.result}" alt="${file.name}" class="file-preview-image">
              <span class="file-preview-name">${file.name}</span>
            `;
          } else {
            preview.innerHTML = `
              <span class="file-preview-icon">📄</span>
              <span class="file-preview-name">${file.name}</span>
            `;
          }
          
          previewContainer.appendChild(preview);
        };
        reader.readAsDataURL(file);
      });
    });
  });

  // ========================================================================
  // INFINITE SCROLL
  // ========================================================================

  const InfiniteScroll = {
    init(options) {
      const sentinel = document.querySelector(options.sentinel);
      if (!sentinel) return;

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting && !this.loading) {
            this.loadMore(options);
          }
        });
      }, {
        rootMargin: '100px'
      });

      observer.observe(sentinel);
    },

    loading: false,
    page: 1,

    async loadMore(options) {
      if (this.loading) return;
      this.loading = true;

      try {
        this.page++;
        const response = await fetch(`${options.url}?page=${this.page}`);
        const data = await response.json();

        if (data.results && data.results.length > 0) {
          const container = document.querySelector(options.container);
          container.insertAdjacentHTML('beforeend', data.html);
        }

        if (!data.has_next) {
          const sentinel = document.querySelector(options.sentinel);
          if (sentinel) sentinel.remove();
        }
      } catch (error) {
        console.error('Infinite scroll error:', error);
      } finally {
        this.loading = false;
      }
    }
  };

  // Initialize infinite scroll if configured
  const infiniteScrollConfig = document.querySelector('[data-infinite-scroll]');
  if (infiniteScrollConfig) {
    InfiniteScroll.init({
      sentinel: '[data-infinite-scroll-sentinel]',
      container: infiniteScrollConfig.dataset.infiniteScroll,
      url: infiniteScrollConfig.dataset.infiniteScrollUrl
    });
  }

  // ========================================================================
  // LAZY LOADING IMAGES
  // ========================================================================

  const LazyLoad = {
    init() {
      const images = document.querySelectorAll('img[data-src]');
      
      const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
            imageObserver.unobserve(img);
          }
        });
      });

      images.forEach(img => imageObserver.observe(img));
    }
  };

  LazyLoad.init();

  // ========================================================================
  // SIDEBAR TOGGLE
  // ========================================================================

  document.querySelectorAll('[data-sidebar-toggle]').forEach(toggle => {
    toggle.addEventListener('click', () => {
      const sidebarId = toggle.dataset.sidebarToggle;
      const sidebar = document.getElementById(sidebarId) || document.querySelector('.sidebar');
      if (sidebar) {
        sidebar.classList.toggle('active');
      }
    });
  });

  // ========================================================================
  // ALERTS WITH AUTO-DISMISS
  // ========================================================================

  document.querySelectorAll('.alert[data-auto-dismiss]').forEach(alert => {
    const duration = parseInt(alert.dataset.autoDismiss) || 5000;
    setTimeout(() => {
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 300);
    }, duration);
  });

  document.querySelectorAll('.alert-close').forEach(closeBtn => {
    closeBtn.addEventListener('click', () => {
      const alert = closeBtn.closest('.alert');
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 300);
    });
  });

  // ========================================================================
  // EXPORT TO WINDOW
  // ========================================================================

  window.GSMInfinity = {
    Modal,
    Dropdown,
    Toast: ToastManager,
    Utils,
    ThemeManager,
    InfiniteScroll,
    LazyLoad
  };

  // Dispatch ready event
  document.dispatchEvent(new CustomEvent('gsm:ready'));

})();
