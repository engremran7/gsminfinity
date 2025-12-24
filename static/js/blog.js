/**
 * Blog Post Enhancement Script
 * Enterprise Edition
 * 
 * Features:
 * - Table of contents generation
 * - Reading progress indicator
 * - Code block copy functionality
 * - Image lightbox
 * - Estimated reading time
 * - Social sharing
 */

(function() {
  'use strict';

  const DEBUG = window.DEBUG || false;
  const log = (msg, data) => DEBUG && console.log(`[Blog] ${msg}`, data || '');

  const BlogEnhancements = {
    /**
     * Initialize all blog enhancements
     */
    init() {
      this.initReadingProgress();
      this.initCodeBlocks();
      this.initTableOfContents();
      this.initImageLightbox();
      this.initSocialSharing();
      this.updateReadingTime();
      log('Blog enhancements initialized');
    },

    /**
     * Reading progress indicator
     */
    initReadingProgress() {
      const progressBar = document.getElementById('reading-progress');
      if (!progressBar) return;

      const article = document.querySelector('article');
      if (!article) return;

      const updateProgress = () => {
        const articleRect = article.getBoundingClientRect();
        const articleTop = articleRect.top + window.scrollY;
        const articleHeight = article.offsetHeight;
        const windowHeight = window.innerHeight;
        const scrollPos = window.scrollY;

        // Calculate progress through the article
        const start = articleTop - windowHeight;
        const end = articleTop + articleHeight;
        const progress = Math.min(100, Math.max(0, 
          ((scrollPos - start) / (end - start)) * 100
        ));

        progressBar.style.width = `${progress}%`;
      };

      window.addEventListener('scroll', window.APP?.throttle?.(updateProgress, 16) || updateProgress);
      updateProgress();
    },

    /**
     * Add copy button to code blocks
     */
    initCodeBlocks() {
      const codeBlocks = document.querySelectorAll('pre code');
      
      codeBlocks.forEach(code => {
        const pre = code.parentElement;
        if (pre.querySelector('.copy-button')) return; // Already has button

        const button = document.createElement('button');
        button.className = 'copy-button absolute top-2 right-2 px-2 py-1 text-xs rounded bg-slate-700 text-slate-300 hover:bg-slate-600 opacity-0 group-hover:opacity-100 transition-opacity';
        button.textContent = 'Copy';
        button.setAttribute('aria-label', 'Copy code to clipboard');

        // Make pre relative for absolute positioning
        pre.classList.add('relative', 'group');
        pre.appendChild(button);

        button.addEventListener('click', async () => {
          const text = code.textContent;
          const success = window.APP?.copyToClipboard 
            ? await window.APP.copyToClipboard(text)
            : await navigator.clipboard.writeText(text).then(() => true).catch(() => false);

          if (success) {
            button.textContent = 'Copied!';
            button.classList.add('bg-green-600');
            setTimeout(() => {
              button.textContent = 'Copy';
              button.classList.remove('bg-green-600');
            }, 2000);
          }
        });
      });
    },

    /**
     * Generate table of contents from headings
     */
    initTableOfContents() {
      const tocContainer = document.getElementById('table-of-contents');
      if (!tocContainer) return;

      const article = document.querySelector('article');
      if (!article) return;

      const headings = article.querySelectorAll('h2, h3');
      if (headings.length < 2) {
        tocContainer.style.display = 'none';
        return;
      }

      const toc = document.createElement('nav');
      toc.setAttribute('aria-label', 'Table of contents');
      toc.className = 'space-y-2';

      const list = document.createElement('ul');
      list.className = 'space-y-1';

      headings.forEach((heading, index) => {
        // Add ID if not present
        if (!heading.id) {
          heading.id = `heading-${index}`;
        }

        const item = document.createElement('li');
        const link = document.createElement('a');
        link.href = `#${heading.id}`;
        link.textContent = heading.textContent;
        link.className = heading.tagName === 'H3' 
          ? 'block pl-4 text-sm text-slate-500 dark:text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400'
          : 'block text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-indigo-600 dark:hover:text-indigo-400';

        item.appendChild(link);
        list.appendChild(item);
      });

      toc.appendChild(list);
      tocContainer.appendChild(toc);
    },

    /**
     * Image lightbox for article images
     */
    initImageLightbox() {
      const article = document.querySelector('article');
      if (!article) return;

      const images = article.querySelectorAll('img:not(.no-lightbox)');
      
      images.forEach(img => {
        if (img.closest('a')) return; // Already wrapped in link

        img.classList.add('cursor-zoom-in');
        img.addEventListener('click', () => this.openLightbox(img.src, img.alt));
      });
    },

    /**
     * Open lightbox with image
     */
    openLightbox(src, alt) {
      const existing = document.getElementById('lightbox');
      if (existing) existing.remove();

      const lightbox = document.createElement('div');
      lightbox.id = 'lightbox';
      lightbox.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4';
      lightbox.innerHTML = `
        <button class="absolute top-4 right-4 text-white text-2xl hover:text-slate-300" aria-label="Close">×</button>
        <img src="${src}" alt="${alt || ''}" class="max-w-full max-h-full object-contain" />
      `;

      lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox || e.target.tagName === 'BUTTON') {
          lightbox.remove();
        }
      });

      document.addEventListener('keydown', function handler(e) {
        if (e.key === 'Escape') {
          lightbox.remove();
          document.removeEventListener('keydown', handler);
        }
      });

      document.body.appendChild(lightbox);
    },

    /**
     * Social sharing buttons
     */
    initSocialSharing() {
      const shareButtons = document.querySelectorAll('[data-share]');
      const pageUrl = encodeURIComponent(window.location.href);
      const pageTitle = encodeURIComponent(document.title);

      shareButtons.forEach(button => {
        const platform = button.dataset.share;
        let shareUrl;

        switch (platform) {
          case 'twitter':
            shareUrl = `https://twitter.com/intent/tweet?url=${pageUrl}&text=${pageTitle}`;
            break;
          case 'facebook':
            shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${pageUrl}`;
            break;
          case 'linkedin':
            shareUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${pageUrl}`;
            break;
          case 'copy':
            button.addEventListener('click', async (e) => {
              e.preventDefault();
              const success = await (window.APP?.copyToClipboard?.(window.location.href) 
                || navigator.clipboard.writeText(window.location.href).then(() => true).catch(() => false));
              if (success) {
                const original = button.innerHTML;
                button.innerHTML = '✓ Copied!';
                setTimeout(() => button.innerHTML = original, 2000);
              }
            });
            return;
        }

        if (shareUrl) {
          button.addEventListener('click', (e) => {
            e.preventDefault();
            window.open(shareUrl, '_blank', 'width=600,height=400');
          });
        }
      });
    },

    /**
     * Update reading time display
     */
    updateReadingTime() {
      const readingTimeEl = document.getElementById('reading-time');
      if (!readingTimeEl) return;

      const article = document.querySelector('article');
      if (!article) return;

      const text = article.textContent || '';
      const wordCount = text.trim().split(/\s+/).length;
      const readingTime = Math.ceil(wordCount / 200); // ~200 words per minute

      readingTimeEl.textContent = `${readingTime} min read`;
    }
  };

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => BlogEnhancements.init());
  } else {
    BlogEnhancements.init();
  }

  // Expose for external access
  window.BlogEnhancements = BlogEnhancements;
})();
