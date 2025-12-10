// Service Worker for Push Notifications
// Version: 1.0.0

const CACHE_NAME = 'gsminfinity-v1';
const urlsToCache = [
  '/',
  '/static/css/enterprise.css',
  '/static/js/main.js'
];

// Install service worker and cache resources
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[Service Worker] Caching app shell');
        return cache.addAll(urlsToCache);
      })
      .catch(err => {
        console.error('[Service Worker] Cache failed:', err);
      })
  );
  self.skipWaiting();
});

// Activate service worker and clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[Service Worker] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Handle push notifications
self.addEventListener('push', event => {
  console.log('[Service Worker] Push received');
  
  let data = {
    title: 'New Notification',
    body: 'You have a new notification',
    icon: '/static/img/logo.png',
    badge: '/static/img/logo.png',
    tag: 'notification',
    url: '/users/notifications/'
  };
  
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }
  
  const options = {
    body: data.body,
    icon: data.icon || '/static/img/logo.png',
    badge: data.badge || '/static/img/logo.png',
    tag: data.tag || 'notification',
    data: {
      url: data.url || '/users/notifications/',
      notificationId: data.notificationId
    },
    vibrate: [200, 100, 200],
    requireInteraction: false,
    actions: [
      {
        action: 'view',
        title: 'View',
        icon: '/static/img/view-icon.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/static/img/close-icon.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  console.log('[Service Worker] Notification clicked');
  
  event.notification.close();
  
  if (event.action === 'dismiss') {
    return;
  }
  
  const urlToOpen = event.notification.data?.url || '/users/notifications/';
  const notificationId = event.notification.data?.notificationId;
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        // Check if there's already a window open
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url.includes(urlToOpen) && 'focus' in client) {
            return client.focus();
          }
        }
        
        // If no window found, open a new one
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen).then(client => {
            // Mark notification as read
            if (notificationId) {
              markNotificationAsRead(notificationId);
            }
            return client;
          });
        }
      })
  );
});

// Handle notification close
self.addEventListener('notificationclose', event => {
  console.log('[Service Worker] Notification closed', event.notification.data);
});

// Helper function to mark notification as read
async function markNotificationAsRead(notificationId) {
  try {
    const response = await fetch(`/users/notifications/${notificationId}/mark-read/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      console.log('[Service Worker] Notification marked as read');
    }
  } catch (error) {
    console.error('[Service Worker] Failed to mark notification as read:', error);
  }
}

// Handle background sync (for offline notification actions)
self.addEventListener('sync', event => {
  console.log('[Service Worker] Background sync:', event.tag);
  
  if (event.tag === 'sync-notifications') {
    event.waitUntil(syncNotifications());
  }
});

async function syncNotifications() {
  try {
    const response = await fetch('/users/notifications/unread-count/');
    if (response.ok) {
      const data = await response.json();
      console.log('[Service Worker] Synced notification count:', data.count);
    }
  } catch (error) {
    console.error('[Service Worker] Sync failed:', error);
  }
}

// Handle messages from clients
self.addEventListener('message', event => {
  console.log('[Service Worker] Message received:', event.data);
  
  if (event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});

console.log('[Service Worker] Loaded successfully');
