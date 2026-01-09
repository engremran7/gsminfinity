#!/usr/bin/env python
"""
Template Link Integrity Audit Script
Verifies all {% url %} tags reference valid URL patterns.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class URLReference:
    """Represents a {% url %} tag in a template."""
    template_file: str
    line_number: int
    url_name: str
    raw_tag: str
    is_valid: bool = True
    issue: str | None = None


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def extract_url_names_from_urls_py(project_root: Path) -> set[str]:
    """Extract all defined URL names from urls.py files."""
    url_names = set()

    # Find all urls.py files
    apps_dir = project_root / "apps"
    urls_files = list(apps_dir.glob("**/urls.py"))
    urls_files.append(project_root / "app" / "urls.py")

    name_pattern = re.compile(r"name\s*=\s*['\"]([^'\"]+)['\"]")
    namespace_pattern = re.compile(r"namespace\s*=\s*['\"]([^'\"]+)['\"]")
    app_name_pattern = re.compile(r"app_name\s*=\s*['\"]([^'\"]+)['\"]")

    for urls_file in urls_files:
        if not urls_file.exists():
            continue

        try:
            with open(urls_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Get namespace/app_name
            app_name_match = app_name_pattern.search(content)
            namespace = app_name_match.group(1) if app_name_match else None

            # Get all URL names
            for match in name_pattern.finditer(content):
                name = match.group(1)
                url_names.add(name)
                if namespace:
                    url_names.add(f"{namespace}:{name}")

        except Exception as e:
            print(f"Error parsing {urls_file}: {e}", file=sys.stderr)

    # Add common Django/allauth URL names
    common_urls = {
        "admin:index", "admin:logout",
        "account_login", "account_logout", "account_signup",
        "account_email", "account_change_password",
        "account_reset_password", "account_reset_password_done",
    }
    url_names.update(common_urls)

    return url_names


def extract_url_references_from_template(template_file: Path) -> list[URLReference]:
    """Extract all {% url %} references from a template."""
    references = []

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Pattern for {% url 'name' %} or {% url "name" %}
        url_pattern = re.compile(r"\{%\s*url\s+['\"]([^'\"]+)['\"]")

        for i, line in enumerate(lines, 1):
            for match in url_pattern.finditer(line):
                references.append(URLReference(
                    template_file=str(template_file),
                    line_number=i,
                    url_name=match.group(1),
                    raw_tag=match.group(0),
                ))

    except Exception as e:
        print(f"Error parsing {template_file}: {e}", file=sys.stderr)

    return references


def detect_hardcoded_urls(template_file: Path) -> list[dict[str, Any]]:
    """Detect hardcoded URLs that should use {% url %}."""
    issues = []

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Pattern for hardcoded admin/app URLs
        hardcoded_pattern = re.compile(
            r'href\s*=\s*["\']/(admin|blog|users|tags|consent|analytics|seo)/',
            re.IGNORECASE
        )

        for i, line in enumerate(lines, 1):
            match = hardcoded_pattern.search(line)
            if match:
                issues.append({
                    "type": "HARDCODED_URL",
                    "severity": "warning",
                    "file": str(template_file),
                    "line": i,
                    "url_fragment": match.group(0),
                    "message": f"Hardcoded URL found - should use {{% url %}} tag",
                })

    except Exception:
        pass

    return issues


def audit_template_links(project_root: Path) -> dict[str, Any]:
    """Audit all template URL references."""
    templates_dir = project_root / "templates"
    apps_dir = project_root / "apps"

    # Get all valid URL names
    valid_urls = extract_url_names_from_urls_py(project_root)

    # Find all templates
    template_files = list(templates_dir.glob("**/*.html"))
    template_files.extend(apps_dir.glob("**/templates/**/*.html"))

    all_references: list[URLReference] = []
    hardcoded_issues: list[dict] = []

    for template_file in template_files:
        refs = extract_url_references_from_template(template_file)
        all_references.extend(refs)

        hardcoded = detect_hardcoded_urls(template_file)
        hardcoded_issues.extend(hardcoded)

    # Validate references
    invalid_refs = []
    for ref in all_references:
        if ref.url_name not in valid_urls:
            # Check if it might be valid with a namespace
            parts = ref.url_name.split(":")
            if len(parts) == 2 and parts[1] not in valid_urls:
                ref.is_valid = False
                ref.issue = f"URL name '{ref.url_name}' not found in URL configuration"
                invalid_refs.append(ref)

    return {
        "summary": {
            "total_url_refs": len(all_references),
            "valid_refs": len(all_references) - len(invalid_refs),
            "invalid_refs": len(invalid_refs),
            "hardcoded_urls": len(hardcoded_issues),
            "unique_url_names": len(set(r.url_name for r in all_references)),
        },
        "invalid_references": [
            {
                "file": r.template_file,
                "line": r.line_number,
                "url_name": r.url_name,
                "issue": r.issue,
            }
            for r in invalid_refs
        ],
        "hardcoded_urls": hardcoded_issues,
        "url_usage": dict(sorted(
            ((url, sum(1 for r in all_references if r.url_name == url))
             for url in set(r.url_name for r in all_references)),
            key=lambda x: -x[1]
        )[:20]),
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")

    report = audit_template_links(project_root)

    print("\n" + "=" * 60)
    print("TEMPLATE LINK INTEGRITY AUDIT")
    print("=" * 60)

    print(f"\n📊 Summary:")
    print(f"   Total URL References: {report['summary']['total_url_refs']}")
    print(f"   Valid References: {report['summary']['valid_refs']}")
    print(f"   Invalid References: {report['summary']['invalid_refs']}")
    print(f"   Hardcoded URLs: {report['summary']['hardcoded_urls']}")

    if report["invalid_references"]:
        print(f"\n❌ Invalid URL References ({len(report['invalid_references'])}):")
        for ref in report["invalid_references"][:10]:
            print(f"   - {ref['file']}:{ref['line']}")
            print(f"     URL: {ref['url_name']}")

    if report["hardcoded_urls"]:
        print(f"\n⚠️  Hardcoded URLs ({len(report['hardcoded_urls'])}):")
        for issue in report["hardcoded_urls"][:10]:
            print(f"   - {issue['file']}:{issue['line']}")
            print(f"     Fragment: {issue['url_fragment']}")

    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "template_link_integrity_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    total_issues = len(report["invalid_references"]) + len(report["hardcoded_urls"])
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
