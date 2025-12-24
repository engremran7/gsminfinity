#!/usr/bin/env python
"""
HTMX Audit Script
Validates HTMX usage patterns, endpoints, and partial templates.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class HTMXUsage:
    """Represents an HTMX attribute usage."""
    template_file: str
    line_number: int
    attribute: str
    value: str
    target: str | None = None
    swap: str | None = None
    trigger: str | None = None


@dataclass
class HTMXEndpoint:
    """Represents an HTMX endpoint."""
    url: str
    method: str
    source_template: str
    has_partial: bool = False
    csrf_protected: bool = True


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def extract_htmx_usages(template_file: Path) -> list[HTMXUsage]:
    """Extract all HTMX attribute usages from a template."""
    usages = []
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        htmx_attrs = [
            "hx-get", "hx-post", "hx-put", "hx-delete", "hx-patch",
            "hx-target", "hx-swap", "hx-trigger", "hx-push-url",
            "hx-select", "hx-select-oob", "hx-vals", "hx-headers",
            "hx-confirm", "hx-indicator", "hx-boost",
        ]
        
        for i, line in enumerate(lines, 1):
            for attr in htmx_attrs:
                pattern = re.compile(rf'{attr}\s*=\s*["\']([^"\']*)["\']')
                for match in pattern.finditer(line):
                    usage = HTMXUsage(
                        template_file=str(template_file),
                        line_number=i,
                        attribute=attr,
                        value=match.group(1),
                    )
                    
                    # Extract related attributes from same element
                    if "hx-target" in line:
                        target_match = re.search(r'hx-target\s*=\s*["\']([^"\']*)["\']', line)
                        if target_match:
                            usage.target = target_match.group(1)
                    
                    if "hx-swap" in line:
                        swap_match = re.search(r'hx-swap\s*=\s*["\']([^"\']*)["\']', line)
                        if swap_match:
                            usage.swap = swap_match.group(1)
                    
                    usages.append(usage)
                    
    except Exception as e:
        print(f"Error parsing {template_file}: {e}", file=sys.stderr)
    
    return usages


def extract_htmx_endpoints(usages: list[HTMXUsage]) -> list[HTMXEndpoint]:
    """Extract unique HTMX endpoints from usages."""
    endpoints = []
    seen = set()
    
    for usage in usages:
        if usage.attribute in ["hx-get", "hx-post", "hx-put", "hx-delete", "hx-patch"]:
            method = usage.attribute.replace("hx-", "").upper()
            url = usage.value
            
            key = (method, url)
            if key not in seen:
                seen.add(key)
                endpoints.append(HTMXEndpoint(
                    url=url,
                    method=method,
                    source_template=usage.template_file,
                ))
    
    return endpoints


def check_csrf_protection(template_file: Path) -> bool:
    """Check if template has CSRF protection for HTMX POST requests."""
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for CSRF token in various forms
        has_csrf_token = "{% csrf_token %}" in content
        has_csrf_meta = 'name="csrf-token"' in content or 'name="csrfmiddlewaretoken"' in content
        has_hx_headers_csrf = "hx-headers" in content and "csrf" in content.lower()
        
        return has_csrf_token or has_csrf_meta or has_hx_headers_csrf
        
    except Exception:
        return False


def detect_htmx_issues(usages: list[HTMXUsage], endpoints: list[HTMXEndpoint]) -> list[dict[str, Any]]:
    """Detect potential HTMX issues."""
    issues = []
    
    # Check for missing targets
    for usage in usages:
        if usage.attribute in ["hx-get", "hx-post"] and not usage.target:
            # Check if there's a default target or if using hx-boost
            issues.append({
                "type": "MISSING_TARGET",
                "severity": "info",
                "file": usage.template_file,
                "line": usage.line_number,
                "attribute": usage.attribute,
                "message": "HTMX request without explicit hx-target (will swap innerHTML of triggering element)",
            })
    
    # Check for POST without CSRF
    templates_with_post = {u.template_file for u in usages if u.attribute == "hx-post"}
    for template in templates_with_post:
        if not check_csrf_protection(Path(template)):
            issues.append({
                "type": "MISSING_CSRF",
                "severity": "warning",
                "file": template,
                "message": "Template has hx-post but no visible CSRF token",
            })
    
    # Check for potentially problematic swap modes
    for usage in usages:
        if usage.swap in ["outerHTML", "delete"]:
            issues.append({
                "type": "DESTRUCTIVE_SWAP",
                "severity": "info",
                "file": usage.template_file,
                "line": usage.line_number,
                "swap": usage.swap,
                "message": f"Using '{usage.swap}' swap mode - ensure this is intentional",
            })
    
    # Check for Django URL tags vs hardcoded URLs
    for usage in usages:
        if usage.attribute in ["hx-get", "hx-post"] and usage.value.startswith("/"):
            if not "{%" in usage.value:
                issues.append({
                    "type": "HARDCODED_URL",
                    "severity": "warning",
                    "file": usage.template_file,
                    "line": usage.line_number,
                    "url": usage.value,
                    "message": "Hardcoded URL in HTMX attribute - prefer {% url %} tag",
                })
    
    return issues


def find_partial_templates(project_root: Path) -> list[str]:
    """Find templates that are likely HTMX partials."""
    partials = []
    
    templates_dir = project_root / "templates"
    apps_dir = project_root / "apps"
    
    partial_patterns = [
        "**/partials/*.html",
        "**/includes/*.html",
        "**/*_partial.html",
        "**/*_fragment.html",
    ]
    
    for pattern in partial_patterns:
        partials.extend(str(p) for p in templates_dir.glob(pattern))
        partials.extend(str(p) for p in apps_dir.glob(f"**/templates/{pattern}"))
    
    return partials


def audit_htmx(project_root: Path) -> dict[str, Any]:
    """Audit HTMX usage."""
    templates_dir = project_root / "templates"
    apps_dir = project_root / "apps"
    
    # Find all templates
    template_files = list(templates_dir.glob("**/*.html"))
    template_files.extend(apps_dir.glob("**/templates/**/*.html"))
    
    # Extract HTMX usages
    all_usages: list[HTMXUsage] = []
    for template in template_files:
        usages = extract_htmx_usages(template)
        all_usages.extend(usages)
    
    # Extract endpoints
    endpoints = extract_htmx_endpoints(all_usages)
    
    # Find partials
    partials = find_partial_templates(project_root)
    
    # Detect issues
    issues = detect_htmx_issues(all_usages, endpoints)
    
    # Check for HTMX script inclusion
    htmx_included = False
    for template in template_files:
        try:
            with open(template, "r", encoding="utf-8") as f:
                if "htmx" in f.read().lower():
                    htmx_included = True
                    break
        except Exception:
            continue
    
    # Group usages by attribute
    by_attribute: dict[str, int] = {}
    for usage in all_usages:
        by_attribute[usage.attribute] = by_attribute.get(usage.attribute, 0) + 1
    
    return {
        "summary": {
            "htmx_included": htmx_included,
            "total_usages": len(all_usages),
            "unique_endpoints": len(endpoints),
            "partial_templates": len(partials),
            "issues_found": len(issues),
        },
        "by_attribute": dict(sorted(by_attribute.items(), key=lambda x: -x[1])),
        "endpoints": [
            {
                "url": e.url,
                "method": e.method,
                "source": e.source_template,
            }
            for e in endpoints
        ],
        "partial_templates": partials[:20],
        "issues": issues,
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")
    
    report = audit_htmx(project_root)
    
    print("\n" + "=" * 60)
    print("HTMX AUDIT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   HTMX Included: {'✅' if report['summary']['htmx_included'] else '❌'}")
    print(f"   Total HTMX Usages: {report['summary']['total_usages']}")
    print(f"   Unique Endpoints: {report['summary']['unique_endpoints']}")
    print(f"   Partial Templates: {report['summary']['partial_templates']}")
    print(f"   Issues Found: {report['summary']['issues_found']}")
    
    print(f"\n📊 Usage by Attribute:")
    for attr, count in list(report["by_attribute"].items())[:10]:
        print(f"   {attr}: {count}")
    
    if report["endpoints"]:
        print(f"\n🔗 HTMX Endpoints ({len(report['endpoints'])}):")
        for ep in report["endpoints"][:10]:
            print(f"   {ep['method']} {ep['url']}")
    
    if report["issues"]:
        print(f"\n⚠️  Issues ({len(report['issues'])}):")
        for issue in report["issues"][:10]:
            icon = "❌" if issue["severity"] == "error" else "⚠️" if issue["severity"] == "warning" else "ℹ️"
            print(f"   {icon} [{issue['type']}] {issue['message']}")
            if "file" in issue:
                print(f"      File: {issue['file']}")
    
    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "htmx_audit_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    error_count = sum(1 for i in report["issues"] if i.get("severity") == "error")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
