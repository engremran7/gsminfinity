/**
 * GSM Infinity - Ads Management JavaScript
 * 
 * Handles client-side ad slot hydration, consent checking,
 * impression tracking, and click tracking.
 * 
 * CSP-compliant, no inline scripts.
 */

(function() {
  'use strict';

  const AdsManager = {
    config: {
      fillEndpoint: '/ads/api/fill/',
      clickEndpoint: '/ads/api/click/',
      eventEndpoint: '/ads/api/events/',
      debug: false
    },

    /**
     * Initialize ads manager
     */
    init() {
      if (!window.FEATURE_FLAGS?.ads_enabled) {
        this.log('Ads disabled via feature flag');
        return;
      }

      this.hydrateAdSlots();
      this.setupClickTracking();
      this.log('Ads manager initialized');
    },

    /**
     * Check if user has given consent for ads
     */
    hasConsent() {
      try {
        const consent = localStorage.getItem('gsm_consent');
        if (consent) {
          const parsed = JSON.parse(consent);
          return parsed.ads === true;
        }
      } catch (e) {
        this.log('Error checking consent', e);
      }
      // Default to true if no consent system or error
      return true;
    },

    /**
     * Hydrate all ad slots on the page
     */
    async hydrateAdSlots() {
      const slots = document.querySelectorAll('[data-ad-slot]');
      
      for (const slot of slots) {
        const slotId = slot.dataset.adSlot;
        const requiresConsent = slot.dataset.requiresConsent === 'ads';
        
        if (requiresConsent && !this.hasConsent()) {
          this.log(`Skipping slot ${slotId} - no consent`);
          continue;
        }

        await this.fillSlot(slot, slotId);
      }
    },

    /**
     * Fill a single ad slot with content from the server
     */
    async fillSlot(slotElement, slotId) {
      try {
        const pageUrl = encodeURIComponent(window.location.href);
        const response = await fetch(
          `${this.config.fillEndpoint}?placement=${encodeURIComponent(slotId)}&page_url=${pageUrl}`,
          {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
          }
        );

        if (!response.ok) {
          this.log(`Failed to fill slot ${slotId}: ${response.status}`);
          return;
        }

        const data = await response.json();
        
        if (data.skipped) {
          this.log(`Slot ${slotId} skipped: ${data.skipped}`);
          return;
        }

        if (data.ok && data.html) {
          slotElement.innerHTML = data.html;
          slotElement.classList.add('ad-slot--filled');
          
          // Track impression
          this.trackEvent('impression', slotId, data.creative_id);
        }
      } catch (error) {
        this.log(`Error filling slot ${slotId}`, error);
      }
    },

    /**
     * Setup click tracking for ad links
     */
    setupClickTracking() {
      document.addEventListener('click', (e) => {
        const adLink = e.target.closest('.ad-slot a, [data-ad-click]');
        if (adLink) {
          const slot = adLink.closest('[data-ad-slot]');
          if (slot) {
            const slotId = slot.dataset.adSlot;
            const creativeId = slot.dataset.creativeId;
            this.trackEvent('click', slotId, creativeId);
          }
        }
      });
    },

    /**
     * Track an ad event (impression, click, etc.)
     */
    async trackEvent(eventType, slotId, creativeId) {
      try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
        
        await fetch(this.config.eventEndpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest'
          },
          credentials: 'same-origin',
          body: JSON.stringify({
            event_type: eventType,
            placement: slotId,
            creative_id: creativeId,
            page_url: window.location.href,
            timestamp: new Date().toISOString()
          })
        });
        
        this.log(`Tracked ${eventType} for slot ${slotId}`);
      } catch (error) {
        this.log(`Error tracking ${eventType}`, error);
      }
    },

    /**
     * Debug logging
     */
    log(message, data) {
      if (this.config.debug || window.DEBUG) {
        console.log(`[Ads] ${message}`, data || '');
      }
    }
  };

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AdsManager.init());
  } else {
    AdsManager.init();
  }

  // Expose globally
  window.AdsManager = AdsManager;

})();

