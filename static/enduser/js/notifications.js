/**
 * Notification System
 * Handles fetching, displaying, and managing user notifications.
 */

(function() {
  'use strict';

  const NotificationSystem = {
    config: {
      endpoints: {
        unreadCount: '/users/notifications/count/unread/',
        list: '/users/notifications/unread.json',
        markRead: '/users/notifications/mark/', // + pk/
        markAllRead: '/users/notifications/mark-all/'
      },
      pollInterval: 60000, // 1 minute
      selectors: {
        toggle: '[data-notify-toggle]',
        badge: '#notify-badge',
        panel: '#notify-panel',
        list: '#notify-list',
        markAll: '#notify-mark-all'
      }
    },

    init: function() {
      if (!window.AUTH_IS_AUTHENTICATED) return;

      this.elements = {
        toggle: document.querySelector(this.config.selectors.toggle),
        badge: document.querySelector(this.config.selectors.badge),
        panel: document.querySelector(this.config.selectors.panel),
        list: document.querySelector(this.config.selectors.list),
        markAll: document.querySelector(this.config.selectors.markAll)
      };

      if (!this.elements.toggle) return;

      this.bindEvents();
      this.startPolling();
      this.fetchUnreadCount(); // Initial fetch
    },

    bindEvents: function() {
      // Toggle panel
      this.elements.toggle.addEventListener('click', (e) => {
        e.stopPropagation();
        this.togglePanel();
      });

      // Close panel when clicking outside
      document.addEventListener('click', (e) => {
        if (this.elements.panel && !this.elements.panel.classList.contains('hidden') && 
            !this.elements.panel.contains(e.target) && 
            !this.elements.toggle.contains(e.target)) {
          this.elements.panel.classList.add('hidden');
        }
      });

      // Mark all read
      if (this.elements.markAll) {
        this.elements.markAll.addEventListener('click', (e) => {
          e.preventDefault();
          this.markAllRead();
        });
      }
    },

    togglePanel: function() {
      const isHidden = this.elements.panel.classList.contains('hidden');
      
      if (isHidden) {
        this.elements.panel.classList.remove('hidden');
        // When opening, we could fetch the latest list via AJAX if we wanted dynamic dropdown content
        // For now, let's just ensure the badge is updated
        this.fetchUnreadCount();
        this.fetchRecentNotifications(); 
      } else {
        this.elements.panel.classList.add('hidden');
      }
    },

    startPolling: function() {
      setInterval(() => {
        this.fetchUnreadCount();
      }, this.config.pollInterval);
    },

    fetchUnreadCount: function() {
      window.APP.fetch(this.config.endpoints.unreadCount)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
          if (data.ok) {
            this.updateBadge(data.unread_count);
          }
        })
        .catch(error => {
          console.error('Error fetching notification count:', error);
        });
    },

    updateBadge: function(count) {
      if (count > 0) {
        this.elements.badge.textContent = count > 99 ? '99+' : count;
        this.elements.badge.classList.remove('hidden');
      } else {
        this.elements.badge.classList.add('hidden');
      }
    },

    fetchRecentNotifications: function() {
      window.APP.fetch(this.config.endpoints.list)
        .then(response => {
            if (!response.ok) throw new Error('Network response was not ok');
            return response.json();
        })
        .then(data => {
            this.renderList(data.items || []);
        })
        .catch(error => {
            console.error('Error fetching notifications:', error);
            this.elements.list.innerHTML = '<div class="p-4 text-center text-sm text-red-500">Failed to load notifications</div>';
        });
    },

    renderList: function(items) {
        if (items.length === 0) {
            this.elements.list.innerHTML = `
                <div class="p-4 text-center text-sm text-slate-500">
                    No unread notifications.
                    <br>
                    <a href="/users/notifications/" class="text-primary hover:underline mt-1 inline-block">View history</a>
                </div>
            `;
            return;
        }

        const html = items.map(item => {
            const icon = this.getIconForPriority(item.priority);
            const url = item.url || `/users/notifications/${item.id}/`;
            
            return `
                <div class="p-3 hover:bg-slate-50 transition-colors relative group">
                    <div class="flex items-start gap-3">
                        <div class="flex-shrink-0 mt-1">
                            ${icon}
                        </div>
                        <div class="flex-1 min-w-0">
                            <a href="${url}" class="block focus:outline-none">
                                <p class="text-sm font-medium text-slate-900 truncate">${this.escapeHtml(item.title)}</p>
                                <p class="text-xs text-slate-500 mt-0.5 line-clamp-2">${this.escapeHtml(item.message)}</p>
                                <p class="text-[10px] text-slate-400 mt-1">${this.formatDate(item.created_at)}</p>
                            </a>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        this.elements.list.innerHTML = html + `
            <div class="p-2 text-center border-t border-slate-100 bg-slate-50 rounded-b-xl">
                <a href="/users/notifications/" class="text-xs font-medium text-primary hover:text-primary-dark">View all notifications</a>
            </div>
        `;
    },

    getIconForPriority: function(priority) {
        if (priority === 'critical' || priority === 'warning') {
            return `<span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-red-100 text-red-600">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
                    </span>`;
        }
        return `<span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg>
                </span>`;
    },

    escapeHtml: function(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    formatDate: function(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        const now = new Date();
        const diff = (now - date) / 1000; // seconds

        if (diff < 60) return 'Just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        return Math.floor(diff / 86400) + 'd ago';
    },

    markAllRead: function() {
      window.APP.fetch(this.config.endpoints.markAllRead, {
        method: 'POST'
      })
      .then(response => {
          if (!response.ok) throw new Error('Network response was not ok');
          return response.json();
      })
      .then(data => {
        if (data.ok) {
          this.updateBadge(0);
          // Optionally clear the list or mark items visually as read
          this.elements.panel.classList.add('hidden');
        }
      })
      .catch(error => {
        console.error('Error marking all read:', error);
      });
    }
  };

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => NotificationSystem.init());
  } else {
    NotificationSystem.init();
  }

})();
