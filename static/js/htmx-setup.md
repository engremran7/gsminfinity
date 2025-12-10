# HTMX Offline Setup Guide

## Download HTMX

1. **Download the latest HTMX version:**
   ```bash
   # Visit: https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js
   # Save as: static/js/htmx.min.js
   ```

2. **Or use curl/wget:**
   ```bash
   cd static/js/
   curl -o htmx.min.js https://unpkg.com/htmx.org@1.9.10/dist/htmx.min.js
   ```

3. **Or use npm (if you have Node.js):**
   ```bash
   npm install htmx.org
   cp node_modules/htmx.org/dist/htmx.min.js static/js/
   ```

## Verify Installation

The file should be placed at: `D:\GsmInfinity\static\js\htmx.min.js`

File size should be approximately 45-50KB (minified).

## Integration

HTMX is already integrated in the base template:

```html
<script src="{% static 'js/htmx.min.js' %}" nonce="{{ request.csp_nonce }}"></script>
<script src="{% static 'js/enterprise.js' %}" nonce="{{ request.csp_nonce }}"></script>
```

## CSP Configuration

HTMX works with our CSP policy because:
- No inline scripts (all via nonce)
- No eval() usage
- All scripts loaded from same origin
- Event handlers attached programmatically

## Testing

After placing htmx.min.js, test with:

```bash
python manage.py runserver
```

Visit any page and check browser console - should see no HTMX errors.

## Features Enabled

With HTMX installed, these features work automatically:

- **hx-get**: Load content dynamically
- **hx-post**: Submit forms via AJAX
- **hx-trigger**: Event-based updates
- **hx-target**: Specify update targets
- **hx-swap**: Control how content is swapped
- **hx-boost**: Progressive enhancement for links

## Examples in Templates

```html
<!-- Load comments dynamically -->
<div hx-get="/api/comments/?post_id={{ post.id }}" 
     hx-trigger="load" 
     hx-target="#comments-container">
    Loading comments...
</div>

<!-- Submit form via AJAX -->
<form hx-post="/comments/create/" 
      hx-target="#comment-list" 
      hx-swap="afterbegin">
    <textarea name="body"></textarea>
    <button type="submit">Post Comment</button>
</form>

<!-- Infinite scroll -->
<div hx-get="/api/posts/?page=2" 
     hx-trigger="revealed" 
     hx-swap="afterend">
</div>
```

## Advanced HTMX Features

### 1. Request Indicators
```html
<div hx-get="/api/data" hx-indicator="#spinner">
    <div id="spinner" class="htmx-indicator">Loading...</div>
</div>
```

### 2. Confirm Before Action
```html
<button hx-delete="/api/item/123" 
        hx-confirm="Are you sure?">
    Delete
</button>
```

### 3. Polling
```html
<div hx-get="/api/status" 
     hx-trigger="every 5s"
     hx-swap="innerHTML">
</div>
```

### 4. Out of Band Swaps
```html
<!-- Server returns multiple elements -->
<div hx-get="/api/update" hx-target="#main">
    <!-- Response includes: -->
    <!-- <div id="main">New content</div> -->
    <!-- <div id="sidebar" hx-swap-oob="true">New sidebar</div> -->
</div>
```

## Troubleshooting

### HTMX not loading
- Check file path: `static/js/htmx.min.js`
- Run `python manage.py collectstatic`
- Check browser console for 404 errors

### CSP blocking HTMX
- Ensure nonce is present: `{{ request.csp_nonce }}`
- Check CSP header includes script-src 'nonce-...'

### HTMX requests failing
- Check CSRF token in forms
- Verify API endpoints are accessible
- Check network tab in browser DevTools

## Production Checklist

- [x] HTMX downloaded and placed in static/js/
- [x] collectstatic run successfully
- [x] CSP nonce configured
- [x] All HTMX attributes tested
- [x] Error handling in place
- [x] Loading indicators working
- [x] Fallback for JavaScript disabled

## Version Management

Current HTMX version: 1.9.10 (December 2024)

To update:
1. Download new version
2. Replace static/js/htmx.min.js
3. Test all HTMX-powered features
4. Update this version number

## Resources

- Official Docs: https://htmx.org/docs/
- Examples: https://htmx.org/examples/
- Discord: https://htmx.org/discord
- GitHub: https://github.com/bigskysoftware/htmx
