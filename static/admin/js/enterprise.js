/**
 * Enterprise Admin Suite - Core JavaScript
 * HTMX integration, AI features, workflow automation
 * CSP-compliant, offline-first, production-ready
 * Version: 2.0.0
 */

(function() {
  'use strict';

  // ============================================================================
  // CORE NAMESPACE
  // ============================================================================

  window.AdminSuite = window.AdminSuite || {};
  const AdminSuite = window.AdminSuite;

  // ============================================================================
  // CONFIGURATION
  // ============================================================================

  AdminSuite.config = {
    apiEndpoints: {
      commandSearch: '/admin-suite/command-search/',
      aiAssist: '/admin-suite/ai-assist/',
      notifications: '/admin-suite/notifications/',
    },
    shortcuts: {
      commandPalette: ['ctrl+k', 'cmd+k'],
      search: ['ctrl+/', 'cmd+/'],
      aiAssist: ['ctrl+shift+a', 'cmd+shift+a'],
    },
    animation: {
      duration: 300,
      easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
    },
  };

  // ============================================================================
  // UTILITIES
  // ============================================================================

  AdminSuite.utils = {
    // Get CSRF token from cookie or meta tag
    getCsrfToken() {
      let token = this.getCookie('csrftoken');
      if (token) return token;
      
      const meta = document.querySelector('meta[name="csrf-token"]') ||
                   document.querySelector('meta[name="csrfmiddlewaretoken"]');
      return meta ? meta.content : '';
    },

    // Get cookie by name
    getCookie(name) {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [key, value] = cookie.trim().split('=');
        if (key === name) {
          return decodeURIComponent(value);
        }
      }
      return null;
    },

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
      return `as-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    },

    // Format date
    formatDate(date, format = 'short') {
      const d = new Date(date);
      if (format === 'short') {
        return d.toLocaleDateString();
      } else if (format === 'long') {
        return d.toLocaleString();
      } else if (format === 'relative') {
        return this.getRelativeTime(d);
      }
      return d.toString();
    },

    // Get relative time (e.g., "2 hours ago")
    getRelativeTime(date) {
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
      return this.formatDate(date, 'short');
    },

    // Escape HTML
    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },

    // Parse query string
    parseQueryString(query) {
      const params = new URLSearchParams(query);
      const result = {};
      for (const [key, value] of params) {
        result[key] = value;
      }
      return result;
    },
  };

  // ============================================================================
  // TOAST NOTIFICATIONS
  // ============================================================================

  AdminSuite.toast = {
    container: null,

    init() {
      if (!this.container) {
        this.container = document.createElement('div');
        this.container.className = 'toast-container';
        document.body.appendChild(this.container);
      }
    },

    show(message, type = 'info', duration = 5000) {
      this.init();

      const toast = document.createElement('div');
      toast.className = `toast alert alert-${type} animate-slide-in-right`;
      toast.innerHTML = `
        <div class="alert-icon">
          ${this.getIcon(type)}
        </div>
        <div class="alert-content">
          <div class="alert-message">${AdminSuite.utils.escapeHtml(message)}</div>
        </div>
        <button class="modal-close" onclick="this.parentElement.remove()">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>
      `;

      this.container.appendChild(toast);

      if (duration > 0) {
        setTimeout(() => {
          toast.classList.add('exit-fade-out');
          setTimeout(() => toast.remove(), 300);
        }, duration);
      }

      return toast;
    },

    getIcon(type) {
      const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M16.666 5L7.5 14.166l-4.166-4.166" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        danger: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2"/><path d="M10 6v4M10 13h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        warning: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M10 2L2 17h16L10 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 8v3M10 14h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="8" stroke="currentColor" stroke-width="2"/><path d="M10 10v4M10 6h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
      };
      return icons[type] || icons.info;
    },

    success(message, duration) {
      return this.show(message, 'success', duration);
    },

    error(message, duration) {
      return this.show(message, 'danger', duration);
    },

    warning(message, duration) {
      return this.show(message, 'warning', duration);
    },

    info(message, duration) {
      return this.show(message, 'info', duration);
    },
  };

  // ============================================================================
  // MODAL MANAGEMENT
  // ============================================================================

  AdminSuite.modal = {
    activeModal: null,

    open(options) {
      const {
        title = 'Modal',
        content = '',
        size = 'md',
        footer = null,
        onClose = null,
      } = options;

      // Close existing modal
      if (this.activeModal) {
        this.close();
      }

      // Create backdrop
      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop';
      backdrop.onclick = () => this.close();

      // Create modal
      const modal = document.createElement('div');
      modal.className = `modal modal-${size}`;
      modal.onclick = (e) => e.stopPropagation();

      // Build modal HTML
      modal.innerHTML = `
        <div class="modal-header">
          <h2 class="modal-title">${AdminSuite.utils.escapeHtml(title)}</h2>
          <button class="modal-close" onclick="AdminSuite.modal.close()">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          ${content}
        </div>
        ${footer ? `<div class="modal-footer">${footer}</div>` : ''}
      `;

      backdrop.appendChild(modal);
      document.body.appendChild(backdrop);

      this.activeModal = {
        backdrop,
        modal,
        onClose,
      };

      // Prevent body scroll
      document.body.style.overflow = 'hidden';

      return modal;
    },

    close() {
      if (!this.activeModal) return;

      const { backdrop, onClose } = this.activeModal;
      
      if (onClose) {
        onClose();
      }

      backdrop.classList.add('exit-fade-out');
      setTimeout(() => {
        backdrop.remove();
        document.body.style.overflow = '';
      }, 300);

      this.activeModal = null;
    },

    confirm(options) {
      const {
        title = 'Confirm',
        message = 'Are you sure?',
        confirmText = 'Confirm',
        cancelText = 'Cancel',
        confirmClass = 'btn-danger',
        onConfirm = null,
        onCancel = null,
      } = options;

      const content = `
        <div class="dialog-confirm">
          <div class="dialog-icon dialog-icon-warning">⚠️</div>
          <p>${AdminSuite.utils.escapeHtml(message)}</p>
        </div>
      `;

      const footer = `
        <button class="btn btn-secondary" onclick="AdminSuite.modal.close()">${AdminSuite.utils.escapeHtml(cancelText)}</button>
        <button class="btn ${confirmClass}" onclick="AdminSuite.modal._handleConfirm()">${AdminSuite.utils.escapeHtml(confirmText)}</button>
      `;

      this._confirmCallback = onConfirm;
      this._cancelCallback = onCancel;

      return this.open({
        title,
        content,
        footer,
        size: 'sm',
        onClose: onCancel,
      });
    },

    _handleConfirm() {
      if (this._confirmCallback) {
        this._confirmCallback();
      }
      this.close();
    },
  };

  // ============================================================================
  // DRAWER / SLIDING PANEL
  // ============================================================================

  AdminSuite.drawer = {
    activeDrawer: null,

    open(options) {
      const {
        title = 'Drawer',
        content = '',
        side = 'right',
        footer = null,
        onClose = null,
      } = options;

      if (this.activeDrawer) {
        this.close();
      }

      const backdrop = document.createElement('div');
      backdrop.className = 'drawer-backdrop';
      backdrop.onclick = () => this.close();

      const drawer = document.createElement('div');
      drawer.className = `drawer drawer-${side}`;
      drawer.onclick = (e) => e.stopPropagation();

      drawer.innerHTML = `
        <div class="drawer-header">
          <h2 class="drawer-title">${AdminSuite.utils.escapeHtml(title)}</h2>
          <button class="drawer-close" onclick="AdminSuite.drawer.close()">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        <div class="drawer-body">
          ${content}
        </div>
        ${footer ? `<div class="drawer-footer">${footer}</div>` : ''}
      `;

      document.body.appendChild(backdrop);
      document.body.appendChild(drawer);

      this.activeDrawer = {
        backdrop,
        drawer,
        onClose,
      };

      document.body.style.overflow = 'hidden';

      return drawer;
    },

    close() {
      if (!this.activeDrawer) return;

      const { backdrop, drawer, onClose } = this.activeDrawer;
      
      if (onClose) {
        onClose();
      }

      backdrop.classList.add('exit-fade-out');
      drawer.classList.add('exit-slide-right');
      
      setTimeout(() => {
        backdrop.remove();
        drawer.remove();
        document.body.style.overflow = '';
      }, 300);

      this.activeDrawer = null;
    },
  };

  // ============================================================================
  // COMMAND PALETTE
  // ============================================================================

  AdminSuite.commandPalette = {
    isOpen: false,
    container: null,
    results: [],

    init() {
      // Register keyboard shortcuts
      document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
          e.preventDefault();
          this.toggle();
        }
        if (e.key === 'Escape' && this.isOpen) {
          this.close();
        }
      });
    },

    toggle() {
      if (this.isOpen) {
        this.close();
      } else {
        this.open();
      }
    },

    open() {
      if (this.isOpen) return;

      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop';
      backdrop.onclick = () => this.close();

      const palette = document.createElement('div');
      palette.className = 'command-palette';
      palette.onclick = (e) => e.stopPropagation();

      palette.innerHTML = `
        <input 
          type="text" 
          class="command-palette-input" 
          placeholder="Type a command or search..."
          id="command-palette-input"
        />
        <div class="command-palette-results" id="command-palette-results">
          <div class="empty-state">
            <div class="empty-state-message">Start typing to search...</div>
          </div>
        </div>
      `;

      backdrop.appendChild(palette);
      document.body.appendChild(backdrop);

      this.container = backdrop;
      this.isOpen = true;

      // Focus input
      const input = document.getElementById('command-palette-input');
      input.focus();

      // Handle input
      input.addEventListener('input', AdminSuite.utils.debounce((e) => {
        this.search(e.target.value);
      }, 300));

      // Handle keyboard navigation
      input.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          this.selectNext();
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          this.selectPrevious();
        } else if (e.key === 'Enter') {
          e.preventDefault();
          this.executeSelected();
        }
      });

      document.body.style.overflow = 'hidden';

      // Load initial commands
      this.search('');
    },

    close() {
      if (!this.isOpen) return;

      this.container.classList.add('exit-fade-out');
      setTimeout(() => {
        this.container.remove();
        document.body.style.overflow = '';
      }, 300);

      this.isOpen = false;
      this.container = null;
    },

    async search(query) {
      const resultsContainer = document.getElementById('command-palette-results');
      if (!resultsContainer) return;

      try {
        const response = await fetch(
          `${AdminSuite.config.apiEndpoints.commandSearch}?q=${encodeURIComponent(query)}`,
          {
            headers: {
              'X-CSRFToken': AdminSuite.utils.getCsrfToken(),
            },
          }
        );

        const data = await response.json();
        this.results = data.commands || [];
        this.render();
      } catch (error) {
        console.error('Command search failed:', error);
        resultsContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-message">Failed to load commands</div>
          </div>
        `;
      }
    },

    render() {
      const resultsContainer = document.getElementById('command-palette-results');
      if (!resultsContainer) return;

      if (this.results.length === 0) {
        resultsContainer.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-message">No commands found</div>
          </div>
        `;
        return;
      }

      resultsContainer.innerHTML = this.results.map((cmd, index) => `
        <div class="command-palette-item ${index === 0 ? 'active' : ''}" data-index="${index}">
          <div class="command-palette-icon">
            ${this.getCommandIcon(cmd.type)}
          </div>
          <div class="command-palette-content">
            <div class="command-palette-title">${AdminSuite.utils.escapeHtml(cmd.title)}</div>
            <div class="command-palette-subtitle">${AdminSuite.utils.escapeHtml(cmd.description || '')}</div>
          </div>
          ${cmd.shortcut ? `
            <div class="command-palette-shortcut">
              ${cmd.shortcut.split('+').map(key => `<span class="command-palette-key">${key}</span>`).join('')}
            </div>
          ` : ''}
        </div>
      `).join('');

      // Add click handlers
      resultsContainer.querySelectorAll('.command-palette-item').forEach((item, index) => {
        item.onclick = () => {
          this.execute(this.results[index]);
        };
      });
    },

    getCommandIcon(type) {
      const icons = {
        navigation: '🧭',
        action: '⚡',
        search: '🔍',
        setting: '⚙️',
        user: '👤',
        security: '🔒',
      };
      return icons[type] || '📄';
    },

    selectNext() {
      const items = document.querySelectorAll('.command-palette-item');
      const activeIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
      const nextIndex = (activeIndex + 1) % items.length;
      
      items[activeIndex]?.classList.remove('active');
      items[nextIndex]?.classList.add('active');
      items[nextIndex]?.scrollIntoView({ block: 'nearest' });
    },

    selectPrevious() {
      const items = document.querySelectorAll('.command-palette-item');
      const activeIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
      const prevIndex = (activeIndex - 1 + items.length) % items.length;
      
      items[activeIndex]?.classList.remove('active');
      items[prevIndex]?.classList.add('active');
      items[prevIndex]?.scrollIntoView({ block: 'nearest' });
    },

    executeSelected() {
      const activeItem = document.querySelector('.command-palette-item.active');
      if (activeItem) {
        const index = parseInt(activeItem.dataset.index);
        this.execute(this.results[index]);
      }
    },

    execute(command) {
      this.close();
      
      if (command.url) {
        window.location.href = command.url;
      } else if (command.action) {
        // Execute custom action
        if (typeof window[command.action] === 'function') {
          window[command.action]();
        }
      }
    },
  };

  // ============================================================================
  // HTMX INTEGRATION
  // ============================================================================

  AdminSuite.htmx = {
    init() {
      // Configure HTMX
      if (typeof htmx !== 'undefined') {
        // Add CSRF token to all HTMX requests
        document.body.addEventListener('htmx:configRequest', (event) => {
          event.detail.headers['X-CSRFToken'] = AdminSuite.utils.getCsrfToken();
        });

        // Show loading indicators
        document.body.addEventListener('htmx:beforeRequest', (event) => {
          const indicator = event.target.querySelector('.htmx-indicator');
          if (indicator) {
            indicator.classList.remove('hidden');
          }
        });

        document.body.addEventListener('htmx:afterRequest', (event) => {
          const indicator = event.target.querySelector('.htmx-indicator');
          if (indicator) {
            indicator.classList.add('hidden');
          }
        });

        // Handle errors
        document.body.addEventListener('htmx:responseError', (event) => {
          AdminSuite.toast.error('Request failed. Please try again.');
          console.error('HTMX error:', event.detail);
        });

        // Show success messages
        document.body.addEventListener('htmx:afterSwap', (event) => {
          const response = event.detail.xhr;
          if (response && response.status === 200) {
            const successMsg = event.target.dataset.successMessage;
            if (successMsg) {
              AdminSuite.toast.success(successMsg);
            }
          }
        });
      }
    },
  };

  // Continued in next part...

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  AdminSuite.init = function() {
    // Debug logging only in development
    if (window.DEBUG) {
      console.log('🚀 Enterprise Admin Suite initialized');
    }
    
    // Initialize modules
    AdminSuite.htmx.init();
    AdminSuite.commandPalette.init();
    
    // Initialize any other components as needed
    this.initScrollAnimations();
    this.initTableActions();
    this.initFormEnhancements();
    
    // Expose to global scope
    window.AdminSuite = AdminSuite;
  };

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AdminSuite.init());
  } else {
    AdminSuite.init();
  }

})();
