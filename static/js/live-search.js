/**
 * Live Search / Autocomplete Component
 * Provides real-time search suggestions as user types
 */

class LiveSearch {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.options = {
            minChars: 2,
            debounceMs: 300,
            maxResults: 10,
            apiUrl: '/firmwares/api/search/autocomplete/',
            searchType: 'all',
            showCategories: true,
            onSelect: null,
            placeholder: 'Search...',
            ...options
        };
        
        this.dropdown = null;
        this.debounceTimer = null;
        this.isOpen = false;
        this.selectedIndex = -1;
        this.results = [];
        this.abortController = null;
        
        this.init();
    }
    
    init() {
        // Create dropdown container
        this.createDropdown();
        
        // Bind events
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        this.input.addEventListener('keydown', this.handleKeydown.bind(this));
        
        // Prevent form submit on enter when dropdown is open
        const form = this.input.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => {
                if (this.isOpen && this.selectedIndex >= 0) {
                    e.preventDefault();
                    this.selectResult(this.selectedIndex);
                }
            });
        }
        
        // Set attributes
        this.input.setAttribute('autocomplete', 'off');
        this.input.setAttribute('aria-autocomplete', 'list');
        this.input.setAttribute('aria-haspopup', 'listbox');
        
        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
                this.closeDropdown();
            }
        });
    }
    
    createDropdown() {
        // Wrap input in relative container if not already
        const wrapper = document.createElement('div');
        wrapper.className = 'live-search-wrapper';
        wrapper.style.position = 'relative';
        wrapper.style.width = '100%';
        
        this.input.parentNode.insertBefore(wrapper, this.input);
        wrapper.appendChild(this.input);
        
        // Create dropdown
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'live-search-dropdown';
        this.dropdown.setAttribute('role', 'listbox');
        this.dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            z-index: 1000;
            margin-top: 4px;
            background: var(--color-surface, #1e293b);
            border: 1px solid var(--color-border, #334155);
            border-radius: 8px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.2);
            max-height: 400px;
            overflow-y: auto;
            display: none;
        `;
        
        wrapper.appendChild(this.dropdown);
    }
    
    handleInput(e) {
        const query = e.target.value.trim();
        
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Abort previous request
        if (this.abortController) {
            this.abortController.abort();
        }
        
        if (query.length < this.options.minChars) {
            this.closeDropdown();
            return;
        }
        
        // Show loading state
        this.showLoading();
        
        // Debounce the search
        this.debounceTimer = setTimeout(() => {
            this.search(query);
        }, this.options.debounceMs);
    }
    
    handleFocus() {
        if (this.input.value.length >= this.options.minChars && this.results.length > 0) {
            this.openDropdown();
        }
    }
    
    handleBlur() {
        // Delay close to allow click on results
        setTimeout(() => {
            this.closeDropdown();
        }, 200);
    }
    
    handleKeydown(e) {
        if (!this.isOpen) return;
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.navigateResults(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.navigateResults(-1);
                break;
            case 'Enter':
                if (this.selectedIndex >= 0) {
                    e.preventDefault();
                    this.selectResult(this.selectedIndex);
                }
                break;
            case 'Escape':
                this.closeDropdown();
                this.input.blur();
                break;
        }
    }
    
    navigateResults(direction) {
        const items = this.dropdown.querySelectorAll('.live-search-item');
        if (items.length === 0) return;
        
        // Remove current highlight
        if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
            items[this.selectedIndex].classList.remove('highlighted');
        }
        
        // Calculate new index
        this.selectedIndex += direction;
        if (this.selectedIndex < 0) this.selectedIndex = items.length - 1;
        if (this.selectedIndex >= items.length) this.selectedIndex = 0;
        
        // Highlight new item
        const item = items[this.selectedIndex];
        item.classList.add('highlighted');
        item.scrollIntoView({ block: 'nearest' });
    }
    
    async search(query) {
        this.abortController = new AbortController();
        
        try {
            const params = new URLSearchParams({
                q: query,
                type: this.options.searchType,
                limit: this.options.maxResults
            });
            
            const response = await fetch(`${this.options.apiUrl}?${params}`, {
                signal: this.abortController.signal,
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) throw new Error('Search failed');
            
            const data = await response.json();
            this.results = data.results || [];
            this.renderResults(data);
            
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Search error:', error);
            this.showError();
        }
    }
    
    renderResults(data) {
        if (data.results.length === 0) {
            this.showNoResults(data.query);
            return;
        }
        
        let html = '';
        
        if (this.options.showCategories) {
            // Group results by type
            const grouped = this.groupByType(data.results);
            
            for (const [type, items] of Object.entries(grouped)) {
                const typeLabel = this.getTypeLabel(type);
                html += `
                    <div class="live-search-category">
                        <div class="live-search-category-header">${typeLabel}</div>
                        ${items.map((item, idx) => this.renderItem(item, data.results.indexOf(item))).join('')}
                    </div>
                `;
            }
        } else {
            html = data.results.map((item, idx) => this.renderItem(item, idx)).join('');
        }
        
        // Add "View all results" link
        html += `
            <div class="live-search-footer">
                <a href="${this.getSearchUrl(data.query)}" class="live-search-view-all">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                    </svg>
                    View all results for "${this.escapeHtml(data.query)}"
                </a>
            </div>
        `;
        
        this.dropdown.innerHTML = html;
        this.selectedIndex = -1;
        this.openDropdown();
        
        // Bind click events
        this.dropdown.querySelectorAll('.live-search-item').forEach((item, idx) => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                this.selectResult(idx);
            });
            item.addEventListener('mouseenter', () => {
                this.dropdown.querySelectorAll('.live-search-item').forEach(i => i.classList.remove('highlighted'));
                item.classList.add('highlighted');
                this.selectedIndex = idx;
            });
        });
    }
    
    renderItem(item, index) {
        const icon = this.getIcon(item.icon || item.type);
        const highlightedName = this.highlightMatch(item.name, this.input.value);
        
        return `
            <div class="live-search-item" data-index="${index}" data-url="${item.url}" role="option">
                <div class="live-search-item-icon">
                    ${icon}
                </div>
                <div class="live-search-item-content">
                    <div class="live-search-item-name">${highlightedName}</div>
                    ${item.subtitle ? `<div class="live-search-item-subtitle">${this.escapeHtml(item.subtitle)}</div>` : ''}
                </div>
                <div class="live-search-item-type">
                    ${this.getTypeBadge(item.type)}
                </div>
            </div>
        `;
    }
    
    getIcon(iconName) {
        const icons = {
            building: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/></svg>`,
            smartphone: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/></svg>`,
            cpu: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>`,
            layers: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>`,
            'file-text': `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`,
            search: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>`
        };
        return icons[iconName] || icons.search;
    }
    
    getTypeBadge(type) {
        const badges = {
            brand: '<span class="badge badge-purple">Brand</span>',
            model: '<span class="badge badge-blue">Model</span>',
            variant: '<span class="badge badge-cyan">Variant</span>',
            firmware: '<span class="badge badge-green">Firmware</span>',
            blog: '<span class="badge badge-amber">Article</span>'
        };
        return badges[type] || '';
    }
    
    getTypeLabel(type) {
        const labels = {
            brand: 'Brands',
            model: 'Models',
            variant: 'Variants',
            firmware: 'Firmwares',
            blog: 'Blog Posts'
        };
        return labels[type] || type;
    }
    
    groupByType(results) {
        return results.reduce((acc, item) => {
            if (!acc[item.type]) acc[item.type] = [];
            acc[item.type].push(item);
            return acc;
        }, {});
    }
    
    highlightMatch(text, query) {
        if (!query) return this.escapeHtml(text);
        const escaped = this.escapeHtml(text);
        const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
        return escaped.replace(regex, '<mark class="live-search-highlight">$1</mark>');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    getSearchUrl(query) {
        return `/firmwares/browse/?q=${encodeURIComponent(query)}`;
    }
    
    selectResult(index) {
        const item = this.results[index];
        if (!item) return;
        
        if (this.options.onSelect) {
            this.options.onSelect(item);
        } else {
            window.location.href = item.url;
        }
        
        this.closeDropdown();
    }
    
    showLoading() {
        this.dropdown.innerHTML = `
            <div class="live-search-loading">
                <div class="live-search-spinner"></div>
                <span>Searching...</span>
            </div>
        `;
        this.openDropdown();
    }
    
    showNoResults(query) {
        this.dropdown.innerHTML = `
            <div class="live-search-empty">
                <svg class="w-8 h-8 text-gray-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p>No results found for "<strong>${this.escapeHtml(query)}</strong>"</p>
                <p class="text-sm text-gray-500 mt-1">Try different keywords or check spelling</p>
            </div>
        `;
        this.openDropdown();
    }
    
    showError() {
        this.dropdown.innerHTML = `
            <div class="live-search-error">
                <svg class="w-6 h-6 text-red-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p>Search failed. Please try again.</p>
            </div>
        `;
        this.openDropdown();
    }
    
    openDropdown() {
        this.dropdown.style.display = 'block';
        this.isOpen = true;
        this.input.setAttribute('aria-expanded', 'true');
    }
    
    closeDropdown() {
        this.dropdown.style.display = 'none';
        this.isOpen = false;
        this.selectedIndex = -1;
        this.input.setAttribute('aria-expanded', 'false');
    }
    
    destroy() {
        if (this.debounceTimer) clearTimeout(this.debounceTimer);
        if (this.abortController) this.abortController.abort();
        this.dropdown?.remove();
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all search inputs with data-live-search attribute
    document.querySelectorAll('[data-live-search]').forEach(input => {
        const options = {
            searchType: input.dataset.searchType || 'all',
            minChars: parseInt(input.dataset.minChars) || 2,
            maxResults: parseInt(input.dataset.maxResults) || 10
        };
        new LiveSearch(input, options);
    });
    
    // Initialize hero search
    const heroSearch = document.querySelector('.hero-search-input, #hero-search-input');
    if (heroSearch && !heroSearch.dataset.liveSearch) {
        new LiveSearch(heroSearch, {
            searchType: 'all',
            maxResults: 8
        });
    }
    
    // Initialize firmware browse search
    const browseSearch = document.querySelector('#search[name="q"]');
    if (browseSearch && !browseSearch.dataset.liveSearch && browseSearch.closest('.browse-filters, form[action*="browse"]')) {
        new LiveSearch(browseSearch, {
            searchType: 'all',
            maxResults: 10
        });
    }
});

// Export for manual initialization
window.LiveSearch = LiveSearch;
