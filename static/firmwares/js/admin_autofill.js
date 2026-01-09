/**
 * Firmware Admin Auto-fill Functionality
 * 
 * Provides client-side functionality for auto-filling brand information
 * from internet sources and AI.
 */

/**
 * Auto-fill brand information from API
 * @param {number} brandId - The brand ID to auto-fill
 * @param {Event} event - The click event (optional, for loading state)
 */
function autofillBrand(brandId, event) {
    if (!brandId) {
        alert('Invalid brand ID');
        return;
    }
    
    // Get CSRF token from cookie or form
    const csrfToken = getCsrfToken();
    if (!csrfToken) {
        alert('CSRF token not found. Please refresh the page.');
        return;
    }
    
    // Show loading state if event is provided
    let button = null;
    let originalText = '';
    if (event && event.target) {
        button = event.target;
        originalText = button.textContent;
        button.textContent = '⏳ Loading...';
        button.disabled = true;
    }
    
    fetch(`/api/firmwares/brand/${brandId}/autofill/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
        
        if (data.success) {
            alert('Auto-fill completed! Refresh the page to see changes.');
            location.reload();
        } else {
            alert('Error: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        if (button) {
            button.textContent = originalText;
            button.disabled = false;
        }
        alert('Error: ' + error.message);
    });
}

/**
 * Get CSRF token from Django form or cookie
 * @returns {string|null} CSRF token or null if not found
 */
function getCsrfToken() {
    // Try to get from form input
    const tokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (tokenInput) {
        return tokenInput.value;
    }
    
    // Try to get from cookie
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    if (cookie) {
        return cookie.split('=')[1];
    }
    
    return null;
}
