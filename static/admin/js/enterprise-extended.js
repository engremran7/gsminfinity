/**
 * Enterprise Admin Suite - Extended Features (Part 2)
 * Table actions, form enhancements, AI assistance, scroll animations
 */

// Extend AdminSuite with additional features
(function() {
  'use strict';

  const AdminSuite = window.AdminSuite;

  // ============================================================================
  // TABLE MANAGEMENT
  // ============================================================================

  AdminSuite.table = {
    init() {
      this.initSorting();
      this.initBulkActions();
      this.initExpandableRows();
      this.initInlineEdit();
    },

    initSorting() {
      document.querySelectorAll('.table-sortable th').forEach(th => {
        th.addEventListener('click', function() {
          const table = this.closest('table');
          const tbody = table.querySelector('tbody');
          const rows = Array.from(tbody.querySelectorAll('tr'));
          const columnIndex = Array.from(this.parentElement.children).indexOf(this);
          const isAscending = !this.classList.contains('sorted-asc');

          // Remove sorting from all headers
          table.querySelectorAll('th').forEach(header => {
            header.classList.remove('sorted-asc', 'sorted-desc');
          });

          // Add sorting to clicked header
          this.classList.add(isAscending ? 'sorted-asc' : 'sorted-desc');

          // Sort rows
          rows.sort((a, b) => {
            const aValue = a.children[columnIndex].textContent.trim();
            const bValue = b.children[columnIndex].textContent.trim();
            
            // Try numeric comparison first
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            if (!isNaN(aNum) && !isNaN(bNum)) {
              return isAscending ? aNum - bNum : bNum - aNum;
            }
            
            // Fall back to string comparison
            return isAscending 
              ? aValue.localeCompare(bValue)
              : bValue.localeCompare(aValue);
          });

          // Re-append rows
          rows.forEach(row => tbody.appendChild(row));
        });
      });
    },

    initBulkActions() {
      // Select all checkbox
      document.querySelectorAll('[data-select-all]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
          const table = this.closest('table');
          const checkboxes = table.querySelectorAll('[data-select-row]');
          checkboxes.forEach(cb => cb.checked = this.checked);
          AdminSuite.table.updateBulkActions(table);
        });
      });

      // Individual row checkboxes
      document.querySelectorAll('[data-select-row]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
          const table = this.closest('table');
          AdminSuite.table.updateBulkActions(table);
        });
      });
    },

    updateBulkActions(table) {
      const checkboxes = table.querySelectorAll('[data-select-row]:checked');
      const bulkActions = document.querySelector('[data-bulk-actions]');
      
      if (bulkActions) {
        if (checkboxes.length > 0) {
          bulkActions.classList.remove('hidden');
          bulkActions.querySelector('[data-selected-count]').textContent = checkboxes.length;
        } else {
          bulkActions.classList.add('hidden');
        }
      }
    },

    initExpandableRows() {
      document.querySelectorAll('[data-expand-toggle]').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
          e.stopPropagation();
          const row = this.closest('tr');
          const expandedRow = row.nextElementSibling;
          
          if (expandedRow && expandedRow.classList.contains('table-expanded-content')) {
            expandedRow.classList.toggle('active');
            this.classList.toggle('expanded');
          }
        });
      });
    },

    initInlineEdit() {
      document.querySelectorAll('[data-inline-edit]').forEach(element => {
        const display = element.querySelector('[data-edit-display]');
        const input = element.querySelector('[data-edit-input]');
        
        if (display && input) {
          display.addEventListener('click', () => {
            display.classList.add('hidden');
            input.classList.remove('hidden');
            input.focus();
          });

          input.addEventListener('blur', () => {
            display.textContent = input.value;
            display.classList.remove('hidden');
            input.classList.add('hidden');
            
            // Trigger save event
            element.dispatchEvent(new CustomEvent('inline-edit-save', {
              detail: { value: input.value }
            }));
          });

          input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
              input.blur();
            } else if (e.key === 'Escape') {
              input.value = display.textContent;
              input.blur();
            }
          });
        }
      });
    },

    exportToCSV(tableId, filename = 'export.csv') {
      const table = document.getElementById(tableId);
      if (!table) return;

      let csv = [];
      const rows = table.querySelectorAll('tr');

      rows.forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = Array.from(cols).map(col => {
          let data = col.textContent.trim();
          return `"${data.replace(/"/g, '""')}"`;
        });
        csv.push(rowData.join(','));
      });

      const csvContent = csv.join('\n');
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);

      AdminSuite.toast.success('Table exported successfully');
    },
  };

  // ============================================================================
  // FORM ENHANCEMENTS
  // ============================================================================

  AdminSuite.form = {
    init() {
      this.initValidation();
      this.initFileUpload();
      this.initAutoSave();
      this.initDependentFields();
    },

    initValidation() {
      document.querySelectorAll('form[data-validate]').forEach(form => {
        form.addEventListener('submit', function(e) {
          if (!AdminSuite.form.validateForm(this)) {
            e.preventDefault();
            AdminSuite.toast.error('Please fix the errors in the form');
          }
        });

        // Real-time validation
        form.querySelectorAll('input, select, textarea').forEach(field => {
          field.addEventListener('blur', function() {
            AdminSuite.form.validateField(this);
          });
        });
      });
    },

    validateForm(form) {
      let isValid = true;
      const fields = form.querySelectorAll('input, select, textarea');

      fields.forEach(field => {
        if (!this.validateField(field)) {
          isValid = false;
        }
      });

      return isValid;
    },

    validateField(field) {
      const value = field.value.trim();
      let isValid = true;
      let errorMessage = '';

      // Required field
      if (field.required && !value) {
        isValid = false;
        errorMessage = 'This field is required';
      }

      // Email validation
      if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          isValid = false;
          errorMessage = 'Please enter a valid email address';
        }
      }

      // URL validation
      if (field.type === 'url' && value) {
        try {
          new URL(value);
        } catch {
          isValid = false;
          errorMessage = 'Please enter a valid URL';
        }
      }

      // Number validation
      if (field.type === 'number' && value) {
        const num = parseFloat(value);
        if (isNaN(num)) {
          isValid = false;
          errorMessage = 'Please enter a valid number';
        }
        if (field.min && num < parseFloat(field.min)) {
          isValid = false;
          errorMessage = `Value must be at least ${field.min}`;
        }
        if (field.max && num > parseFloat(field.max)) {
          isValid = false;
          errorMessage = `Value must be at most ${field.max}`;
        }
      }

      // Pattern validation
      if (field.pattern && value) {
        const regex = new RegExp(field.pattern);
        if (!regex.test(value)) {
          isValid = false;
          errorMessage = field.title || 'Invalid format';
        }
      }

      // Update UI
      this.updateFieldValidation(field, isValid, errorMessage);

      return isValid;
    },

    updateFieldValidation(field, isValid, errorMessage) {
      const fieldWrapper = field.closest('.form-field');
      if (!fieldWrapper) return;

      const errorElement = fieldWrapper.querySelector('.form-error') ||
                          (() => {
                            const el = document.createElement('div');
                            el.className = 'form-error';
                            fieldWrapper.appendChild(el);
                            return el;
                          })();

      if (isValid) {
        field.classList.remove('input-error');
        field.classList.add('input-success');
        errorElement.textContent = '';
        errorElement.classList.add('hidden');
      } else {
        field.classList.remove('input-success');
        field.classList.add('input-error');
        errorElement.textContent = errorMessage;
        errorElement.classList.remove('hidden');
      }
    },

    initFileUpload() {
      document.querySelectorAll('.file-upload').forEach(container => {
        const input = container.querySelector('.file-upload-input');
        const label = container.querySelector('.file-upload-label');

        if (!input || !label) return;

        // Click to select files
        label.addEventListener('click', () => input.click());

        // Drag and drop
        label.addEventListener('dragover', (e) => {
          e.preventDefault();
          label.classList.add('dragover');
        });

        label.addEventListener('dragleave', () => {
          label.classList.remove('dragover');
        });

        label.addEventListener('drop', (e) => {
          e.preventDefault();
          label.classList.remove('dragover');
          input.files = e.dataTransfer.files;
          this.handleFileSelect(input);
        });

        // File selection
        input.addEventListener('change', () => {
          this.handleFileSelect(input);
        });
      });
    },

    handleFileSelect(input) {
      const files = Array.from(input.files);
      const container = input.closest('.file-upload');
      let listElement = container.querySelector('.file-list');

      if (!listElement) {
        listElement = document.createElement('div');
        listElement.className = 'file-list';
        container.appendChild(listElement);
      }

      listElement.innerHTML = files.map((file, index) => `
        <div class="file-item">
          <div class="file-info">
            <div class="file-icon">📄</div>
            <div class="file-details">
              <div class="file-name">${AdminSuite.utils.escapeHtml(file.name)}</div>
              <div class="file-size">${this.formatFileSize(file.size)}</div>
            </div>
          </div>
          <button type="button" class="file-remove" data-file-index="${index}">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      `).join('');

      // Add remove handlers
      listElement.querySelectorAll('.file-remove').forEach(btn => {
        btn.addEventListener('click', function() {
          const index = parseInt(this.dataset.fileIndex);
          const dt = new DataTransfer();
          const files = Array.from(input.files);
          files.forEach((file, i) => {
            if (i !== index) dt.items.add(file);
          });
          input.files = dt.files;
          AdminSuite.form.handleFileSelect(input);
        });
      });
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    },

    initAutoSave() {
      document.querySelectorAll('form[data-autosave]').forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        const saveDelay = parseInt(form.dataset.autosaveDelay) || 3000;

        inputs.forEach(input => {
          input.addEventListener('input', AdminSuite.utils.debounce(() => {
            this.autoSave(form);
          }, saveDelay));
        });
      });
    },

    autoSave(form) {
      const data = new FormData(form);
      const endpoint = form.dataset.autosaveEndpoint || form.action;

      fetch(endpoint, {
        method: 'POST',
        body: data,
        headers: {
          'X-CSRFToken': AdminSuite.utils.getCsrfToken(),
          'X-Auto-Save': 'true',
        },
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          AdminSuite.toast.info('Draft saved', 2000);
        }
      })
      .catch(error => {
        console.error('Auto-save failed:', error);
      });
    },

    initDependentFields() {
      document.querySelectorAll('[data-depends-on]').forEach(field => {
        const dependsOn = field.dataset.dependsOn;
        const dependsValue = field.dataset.dependsValue;
        const controller = document.querySelector(`[name="${dependsOn}"]`);

        if (controller) {
          const checkVisibility = () => {
            const matches = dependsValue 
              ? controller.value === dependsValue
              : controller.checked;
            
            field.style.display = matches ? '' : 'none';
            if (!matches) {
              // Clear value when hidden
              if (field.tagName === 'INPUT' || field.tagName === 'TEXTAREA') {
                field.value = '';
              }
            }
          };

          controller.addEventListener('change', checkVisibility);
          checkVisibility(); // Initial check
        }
      });
    },
  };

  // ============================================================================
  // SCROLL ANIMATIONS
  // ============================================================================

  AdminSuite.initScrollAnimations = function() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, {
      threshold: 0.1,
    });

    document.querySelectorAll('.scroll-fade-in, .scroll-slide-left, .scroll-slide-right, .scroll-scale-in').forEach(el => {
      observer.observe(el);
    });
  };

  // ============================================================================
  // TABLE ACTIONS INITIALIZATION
  // ============================================================================

  AdminSuite.initTableActions = function() {
    AdminSuite.table.init();
  };

  // ============================================================================
  // FORM ENHANCEMENTS INITIALIZATION
  // ============================================================================

  AdminSuite.initFormEnhancements = function() {
    AdminSuite.form.init();
  };

  // ============================================================================
  // AI ASSISTANT
  // ============================================================================

  AdminSuite.ai = {
    isOpen: false,

    open() {
      AdminSuite.drawer.open({
        title: '🤖 AI Assistant',
        side: 'right',
        content: `
          <div class="ai-assistant">
            <div class="ai-chat" id="ai-chat">
              <div class="ai-message bot">
                <div class="ai-avatar">🤖</div>
                <div class="ai-content">
                  Hello! I'm your admin assistant. How can I help you today?
                </div>
              </div>
            </div>
            <div class="ai-input-wrapper">
              <textarea 
                id="ai-input" 
                class="textarea" 
                placeholder="Ask me anything..."
                rows="3"
              ></textarea>
              <button class="btn btn-primary" onclick="AdminSuite.ai.sendMessage()">
                Send
              </button>
            </div>
          </div>
        `,
        footer: `
          <div class="text-sm text-muted">
            ℹ️ AI responses are generated and may not always be accurate
          </div>
        `,
      });

      this.isOpen = true;

      // Handle Enter key
      setTimeout(() => {
        document.getElementById('ai-input')?.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            this.sendMessage();
          }
        });
      }, 100);
    },

    async sendMessage() {
      const input = document.getElementById('ai-input');
      if (!input) return;

      const message = input.value.trim();
      if (!message) return;

      const chat = document.getElementById('ai-chat');
      if (!chat) return;

      // Add user message
      const userMsg = document.createElement('div');
      userMsg.className = 'ai-message user';
      userMsg.innerHTML = `
        <div class="ai-content">${AdminSuite.utils.escapeHtml(message)}</div>
        <div class="ai-avatar">👤</div>
      `;
      chat.appendChild(userMsg);

      // Clear input
      input.value = '';

      // Add loading indicator
      const loadingMsg = document.createElement('div');
      loadingMsg.className = 'ai-message bot';
      loadingMsg.innerHTML = `
        <div class="ai-avatar">🤖</div>
        <div class="ai-content">
          <div class="loading-dots">
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
          </div>
        </div>
      `;
      chat.appendChild(loadingMsg);
      chat.scrollTop = chat.scrollHeight;

      try {
        const response = await fetch(AdminSuite.config.apiEndpoints.aiAssist, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': AdminSuite.utils.getCsrfToken(),
          },
          body: JSON.stringify({ message }),
        });

        const data = await response.json();

        // Remove loading indicator
        loadingMsg.remove();

        // Add bot response
        const botMsg = document.createElement('div');
        botMsg.className = 'ai-message bot';
        botMsg.innerHTML = `
          <div class="ai-avatar">🤖</div>
          <div class="ai-content">${AdminSuite.utils.escapeHtml(data.response || 'Sorry, I couldn\'t process that.')}</div>
        `;
        chat.appendChild(botMsg);
        chat.scrollTop = chat.scrollHeight;
      } catch (error) {
        console.error('AI request failed:', error);
        loadingMsg.remove();
        
        const errorMsg = document.createElement('div');
        errorMsg.className = 'ai-message bot';
        errorMsg.innerHTML = `
          <div class="ai-avatar">🤖</div>
          <div class="ai-content">Sorry, I encountered an error. Please try again.</div>
        `;
        chat.appendChild(errorMsg);
      }
    },
  };

  // Register keyboard shortcut for AI assistant
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'A') {
      e.preventDefault();
      if (!AdminSuite.ai.isOpen) {
        AdminSuite.ai.open();
      }
    }
  });

  // ============================================================================
  // CONTEXT MENU
  // ============================================================================

  AdminSuite.contextMenu = {
    currentMenu: null,

    show(event, items) {
      event.preventDefault();

      // Remove existing menu
      this.hide();

      // Create menu
      const menu = document.createElement('div');
      menu.className = 'context-menu active';
      menu.style.left = event.pageX + 'px';
      menu.style.top = event.pageY + 'px';

      menu.innerHTML = items.map(item => {
        if (item.divider) {
          return '<div class="dropdown-divider"></div>';
        }
        return `
          <div class="dropdown-item ${item.danger ? 'dropdown-item-danger' : ''}" data-action="${item.action || ''}">
            ${item.icon ? `<span>${item.icon}</span>` : ''}
            ${AdminSuite.utils.escapeHtml(item.label)}
          </div>
        `;
      }).join('');

      document.body.appendChild(menu);
      this.currentMenu = menu;

      // Add click handlers
      menu.querySelectorAll('[data-action]').forEach(item => {
        item.addEventListener('click', () => {
          const action = item.dataset.action;
          const itemConfig = items.find(i => i.action === action);
          if (itemConfig && itemConfig.handler) {
            itemConfig.handler();
          }
          this.hide();
        });
      });

      // Close on click outside
      setTimeout(() => {
        document.addEventListener('click', () => this.hide(), { once: true });
      }, 10);
    },

    hide() {
      if (this.currentMenu) {
        this.currentMenu.remove();
        this.currentMenu = null;
      }
    },
  };

})();
