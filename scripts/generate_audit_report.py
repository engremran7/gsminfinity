#!/usr/bin/env python3
"""
Comprehensive Frontend & Static Files Audit Report Generator
Generates complete inventory of templates, static files, and CSS/contrast issues
"""

import json
import re
from collections import defaultdict
from pathlib import Path


def scan_templates():
    """Scan all templates and categorize by section"""
    templates = defaultdict(list)
    base = Path("templates")

    for html_file in base.rglob("*.html"):
        rel_path = html_file.relative_to(base)
        section = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"
        templates[section].append({
            "file": str(rel_path),
            "path": str(html_file),
            "is_admin": "admin" in str(rel_path).lower(),
            "is_enduser": not ("admin" in str(rel_path).lower())
        })

    return dict(sorted(templates.items()))

def scan_static_files():
    """Scan all static files and categorize"""
    static = defaultdict(lambda: defaultdict(list))
    base = Path("static")

    if not base.exists():
        return {}

    # Categorize by type and audience
    for file_path in base.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(base)
            parts = rel_path.parts

            if len(parts) >= 2:
                file_type = parts[0]  # css, js, img, fonts, etc.
                audience = parts[1] if len(parts) > 2 else "enduser"  # admin vs enduser
                filename = file_path.name

                static[file_type][audience].append({
                    "file": filename,
                    "path": str(rel_path),
                    "size": file_path.stat().st_size
                })

    return {k: dict(v) for k, v in static.items()}

def check_color_contrast(file_path):
    """Check for color contrast issues in CSS files"""
    issues = []
    contrast_pattern = re.compile(r'color\s*:\s*([#\w]+);?\s*.*?background[-a-z]*\s*:\s*([#\w]+);?', re.IGNORECASE)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = contrast_pattern.findall(content)
            if matches:
                for color1, color2 in matches:
                    issues.append(f"Potential contrast issue: {color1} on {color2}")
    except Exception as e:
        pass

    return issues

def scan_css_files():
    """Scan CSS files for potential issues"""
    issues = defaultdict(list)
    base = Path("static/css")

    if not base.exists():
        return {}

    for css_file in base.rglob("*.css"):
        file_issues = check_color_contrast(css_file)
        if file_issues:
            issues[str(css_file.relative_to(base))] = file_issues

    return dict(issues)

def generate_report():
    """Generate comprehensive audit report"""
    report = {
        "metadata": {
            "repo": "GSM Infinity (Renamed to 'app')",
            "audit_type": "Full Frontend & Static Files Assessment",
            "sections": [
                "Admin Frontend",
                "Admin Backend",
                "Enduser Frontend",
                "Enduser Backend",
                "Crawler Guard",
                "Enterprise Features",
                "Audit & Security"
            ]
        },
        "templates": scan_templates(),
        "static_files": scan_static_files(),
        "color_contrast_issues": scan_css_files(),
        "summary": {
            "total_templates": sum(len(files) for files in scan_templates().values()),
            "admin_templates": len([f for templates in scan_templates().values() for f in templates if f["is_admin"]]),
            "enduser_templates": len([f for templates in scan_templates().values() for f in templates if f["is_enduser"]]),
        }
    }

    return report

if __name__ == "__main__":
    report = generate_report()

    # Write JSON report
    with open("_frontend_audit_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("✅ Frontend Audit Report Generated")
    print(f"\nTemplate Summary:")
    print(f"  Total Templates: {report['summary']['total_templates']}")
    print(f"  Admin Templates: {report['summary']['admin_templates']}")
    print(f"  Enduser Templates: {report['summary']['enduser_templates']}")

    print(f"\nTemplate Sections:")
    for section, files in report['templates'].items():
        print(f"  {section}: {len(files)} files")

    print(f"\nStatic File Categories:")
    for file_type, audiences in report['static_files'].items():
        total = sum(len(files) for files in audiences.values())
        print(f"  {file_type}: {total} files")
