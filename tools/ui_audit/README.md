# GSM Infinity UI Audit Tools

Enterprise-grade UI audit suite for Django + Tailwind + HTMX projects.

## Quick Start

```bash
# Run all audits
python tools/ui_audit/run_all.py

# Run individual audits
python tools/ui_audit/url_map.py
python tools/ui_audit/template_render_map.py
python tools/ui_audit/template_link_integrity.py
python tools/ui_audit/static_integrity.py
python tools/ui_audit/template_duplicate_scan.py
python tools/ui_audit/tailwind_audit.py
python tools/ui_audit/htmx_audit.py
python tools/ui_audit/csp_audit.py
python tools/ui_audit/js_duplication_scan.py
```

## Audit Scripts

| Script | Purpose |
|--------|---------|
| `url_map.py` | Maps URL patterns to views and templates |
| `template_render_map.py` | Tracks view→template coupling |
| `template_link_integrity.py` | Validates {% url %} tags |
| `static_integrity.py` | Validates {% static %} references |
| `template_duplicate_scan.py` | Detects duplicate templates |
| `tailwind_audit.py` | Validates Tailwind usage |
| `htmx_audit.py` | Audits HTMX patterns |
| `csp_audit.py` | CSP compliance checking |
| `js_duplication_scan.py` | JavaScript duplication detection |
| `run_all.py` | Runs all audits and generates summary |

## Output

Each script generates:
- Console output with summary
- JSON report in `tools/ui_audit/`

## CI Integration

```yaml
# GitHub Actions example
- name: Run UI Audit
  run: python tools/ui_audit/run_all.py
  
- name: Upload Reports
  uses: actions/upload-artifact@v3
  with:
    name: ui-audit-reports
    path: tools/ui_audit/*.json
```

## Exit Codes

- `0` - Audit passed (no errors)
- `1` - Audit failed (errors found)

## Requirements

- Python 3.10+
- No external dependencies (uses only stdlib)
