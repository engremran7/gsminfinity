/**
 * CSP-Compliant Event Handlers
 * Replaces all inline onclick/onsubmit/onchange handlers for CSP compliance
 * Version: 1.0.0
 */

(function() {
  'use strict';

  // ============================================================================
  // CONFIRMATION DIALOGS
  // ============================================================================
  
  /**
   * Generic confirmation handler for forms and buttons
   * Usage: data-confirm="Are you sure?"
   */
  function setupConfirmHandlers() {
    // Form submissions with confirmation
    document.querySelectorAll('form[data-confirm]').forEach(function(form) {
      form.addEventListener('submit', function(e) {
        if (!confirm(this.dataset.confirm)) {
          e.preventDefault();
        }
      });
    });

    // Buttons with confirmation (that submit parent form)
    document.querySelectorAll('button[data-confirm]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        if (!confirm(this.dataset.confirm)) {
          e.preventDefault();
        }
      });
    });
  }

  // ============================================================================
  // MODAL HANDLERS
  // ============================================================================
  
  /**
   * Open modal by ID
   * Usage: data-modal-open="modal-id"
   */
  function setupModalOpenHandlers() {
    document.querySelectorAll('[data-modal-open]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var modalId = this.dataset.modalOpen;
        var modal = document.getElementById(modalId);
        if (modal) {
          modal.classList.remove('hidden');
        }
      });
    });
  }

  /**
   * Close modal by ID
   * Usage: data-modal-close="modal-id" or data-modal-close (closes parent modal)
   */
  function setupModalCloseHandlers() {
    document.querySelectorAll('[data-modal-close]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var modalId = this.dataset.modalClose;
        var modal;
        if (modalId) {
          modal = document.getElementById(modalId);
        } else {
          // Find closest modal ancestor
          modal = this.closest('[id$="-modal"]');
        }
        if (modal) {
          modal.classList.add('hidden');
        }
      });
    });
  }

  // ============================================================================
  // TOAST/NOTIFICATION HANDLERS
  // ============================================================================
  
  /**
   * Dismiss toast notification
   * Usage: data-dismiss="toast"
   */
  function setupDismissHandlers() {
    document.querySelectorAll('[data-dismiss="toast"]').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var toast = this.closest('.toast-item');
        if (toast) {
          toast.remove();
        }
      });
    });
  }

  // ============================================================================
  // LANGUAGE SWITCHER
  // ============================================================================
  
  /**
   * Language switcher with flag update
   * Usage: data-lang-switch on select element
   */
  function setupLangSwitcher() {
    var langSwitch = document.querySelector('[data-lang-switch]');
    if (langSwitch) {
      langSwitch.addEventListener('change', function() {
        // Update flag if updateLangFlag function exists
        if (typeof window.updateLangFlag === 'function') {
          window.updateLangFlag(this);
        }
        // Submit the parent form
        var form = this.closest('form');
        if (form) {
          form.submit();
        }
      });
    }
  }

  // ============================================================================
  // COOKIE CONSENT
  // ============================================================================
  
  /**
   * Open cookie consent dialog
   * Usage: data-cookie-consent
   */
  function setupCookieConsentHandlers() {
    document.querySelectorAll('[data-cookie-consent]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('open-cookie-consent'));
      });
    });
  }

  // ============================================================================
  // TAG SUBSCRIPTION
  // ============================================================================
  
  /**
   * Subscribe to tag
   * Usage: data-subscribe-tag="tag-slug"
   */
  function setupTagSubscriptionHandlers() {
    document.querySelectorAll('[data-subscribe-tag]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var tagSlug = this.dataset.subscribeTag;
        if (typeof window.subscribeToTag === 'function') {
          window.subscribeToTag(tagSlug);
        }
      });
    });
  }

  // ============================================================================
  // COMMENT HANDLERS
  // ============================================================================
  
  /**
   * Vote on comment
   * Usage: data-vote-comment="123" data-vote-type="upvote|downvote"
   */
  function setupCommentVoteHandlers() {
    document.querySelectorAll('[data-vote-comment]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var commentId = this.dataset.voteComment;
        var voteType = this.dataset.voteType;
        if (typeof window.voteComment === 'function') {
          window.voteComment(parseInt(commentId), voteType);
        }
      });
    });
  }

  /**
   * React to comment
   * Usage: data-react-comment="123" data-reaction-type="like"
   */
  function setupCommentReactionHandlers() {
    document.querySelectorAll('[data-react-comment]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var commentId = this.dataset.reactComment;
        var reactionType = this.dataset.reactionType;
        if (typeof window.reactToComment === 'function') {
          window.reactToComment(parseInt(commentId), reactionType);
        }
      });
    });
  }

  /**
   * Reply to comment
   * Usage: data-reply-comment="123" data-reply-author="username"
   */
  function setupCommentReplyHandlers() {
    document.querySelectorAll('[data-reply-comment]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var commentId = this.dataset.replyComment;
        var author = this.dataset.replyAuthor;
        if (typeof window.replyToComment === 'function') {
          window.replyToComment(parseInt(commentId), author);
        }
      });
    });
  }

  /**
   * Bookmark comment
   * Usage: data-bookmark-comment="123"
   */
  function setupCommentBookmarkHandlers() {
    document.querySelectorAll('[data-bookmark-comment]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var commentId = this.dataset.bookmarkComment;
        if (typeof window.bookmarkComment === 'function') {
          window.bookmarkComment(parseInt(commentId));
        }
      });
    });
  }

  /**
   * Flag comment
   * Usage: data-flag-comment="123"
   */
  function setupCommentFlagHandlers() {
    document.querySelectorAll('[data-flag-comment]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var commentId = this.dataset.flagComment;
        if (typeof window.flagComment === 'function') {
          window.flagComment(parseInt(commentId));
        }
      });
    });
  }

  /**
   * Load replies
   * Usage: data-load-replies="123"
   */
  function setupLoadRepliesHandlers() {
    document.querySelectorAll('[data-load-replies]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var commentId = this.dataset.loadReplies;
        if (typeof window.loadReplies === 'function') {
          window.loadReplies(parseInt(commentId));
        }
      });
    });
  }

  // ============================================================================
  // I18N EDIT MODAL
  // ============================================================================
  
  /**
   * Open edit modal for translations
   * Usage: data-edit-translation="123" data-translation-key="key_name"
   */
  function setupEditTranslationHandlers() {
    document.querySelectorAll('[data-edit-translation]').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.preventDefault();
        var keyId = this.dataset.editTranslation;
        var keyName = this.dataset.translationKey;
        if (typeof window.openEditModal === 'function') {
          window.openEditModal(parseInt(keyId), keyName);
        }
      });
    });
  }

  // ============================================================================
  // PROVIDER FIELD UPDATES
  // ============================================================================
  
  /**
   * Update provider fields on select change
   * Usage: data-provider-select
   */
  function setupProviderSelectHandlers() {
    document.querySelectorAll('[data-provider-select]').forEach(function(select) {
      select.addEventListener('change', function() {
        if (typeof window.updateProviderFields === 'function') {
          window.updateProviderFields();
        }
      });
    });
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================
  
  function initAllHandlers() {
    setupConfirmHandlers();
    setupModalOpenHandlers();
    setupModalCloseHandlers();
    setupDismissHandlers();
    setupLangSwitcher();
    setupCookieConsentHandlers();
    setupTagSubscriptionHandlers();
    setupCommentVoteHandlers();
    setupCommentReactionHandlers();
    setupCommentReplyHandlers();
    setupCommentBookmarkHandlers();
    setupCommentFlagHandlers();
    setupLoadRepliesHandlers();
    setupEditTranslationHandlers();
    setupProviderSelectHandlers();
  }

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAllHandlers);
  } else {
    initAllHandlers();
  }

  // Re-initialize after HTMX swaps
  document.addEventListener('htmx:afterSwap', initAllHandlers);
  document.addEventListener('htmx:afterSettle', initAllHandlers);

})();
