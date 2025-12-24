#!/usr/bin/env python
"""
URL Map Audit Script
Extracts all URL patterns and maps them to views and templates.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class URLMapping:
    """Represents a URL pattern mapping."""
    pattern: str
    name: str
    view: str
    app: str
    methods: list[str] = field(default_factory=list)
    template: str | None = None
    is_api: bool = False
    issues: list[str] = field(default_factory=list)


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def extract_urlpatterns(urls_file: Path) -> list[dict[str, Any]]:
    """Extract URL patterns from a urls.py file using AST."""
    patterns = []
    
    try:
        with open(urls_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for path() calls
        path_pattern = re.compile(
            r"path\(\s*['\"]([^'\"]*)['\"],\s*(\w+(?:\.\w+)*|\w+\.as_view\(\))",
            re.MULTILINE
        )
        
        for match in path_pattern.finditer(content):
            patterns.append({
                "pattern": match.group(1),
                "view": match.group(2),
                "file": str(urls_file),
            })
        
        # Look for name= in path calls
        name_pattern = re.compile(
            r"path\([^)]+name\s*=\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE
        )
        
        for i, match in enumerate(name_pattern.finditer(content)):
            if i < len(patterns):
                patterns[i]["name"] = match.group(1)
                
    except Exception as e:
        print(f"Error parsing {urls_file}: {e}", file=sys.stderr)
    
    return patterns


def find_template_in_view(view_file: Path, view_name: str) -> str | None:
    """Find template rendered by a view function or class."""
    try:
        with open(view_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Look for render() calls near the view
        render_pattern = re.compile(
            rf"def\s+{view_name}\s*\([^)]*\).*?render\s*\(\s*request\s*,\s*['\"]([^'\"]+)['\"]",
            re.DOTALL
        )
        match = render_pattern.search(content)
        if match:
            return match.group(1)
        
        # Look for template_name in class-based views
        template_pattern = re.compile(
            rf"class\s+{view_name}\s*\([^)]*\).*?template_name\s*=\s*['\"]([^'\"]+)['\"]",
            re.DOTALL
        )
        match = template_pattern.search(content)
        if match:
            return match.group(1)
            
    except Exception:
        pass
    
    return None


def audit_url_mappings(project_root: Path) -> list[URLMapping]:
    """Audit all URL mappings in the project."""
    mappings = []
    apps_dir = project_root / "apps"
    
    # Find all urls.py files
    urls_files = list(apps_dir.glob("**/urls.py"))
    urls_files.append(project_root / "app" / "urls.py")
    
    for urls_file in urls_files:
        if not urls_file.exists():
            continue
            
        app_name = urls_file.parent.name
        if app_name == "app":
            app_name = "root"
        
        patterns = extract_urlpatterns(urls_file)
        views_file = urls_file.parent / "views.py"
        
        for p in patterns:
            mapping = URLMapping(
                pattern=p.get("pattern", ""),
                name=p.get("name", "unnamed"),
                view=p.get("view", "unknown"),
                app=app_name,
            )
            
            # Check if it's an API endpoint
            if "api" in mapping.pattern.lower() or "json" in mapping.view.lower():
                mapping.is_api = True
            
            # Try to find template
            if views_file.exists() and not mapping.is_api:
                view_name = mapping.view.split(".")[-1].replace(".as_view()", "")
                mapping.template = find_template_in_view(views_file, view_name)
                
                if not mapping.template and not mapping.is_api:
                    mapping.issues.append("No template found for view")
            
            mappings.append(mapping)
    
    return mappings


def generate_report(mappings: list[URLMapping]) -> dict[str, Any]:
    """Generate a structured audit report."""
    report = {
        "summary": {
            "total_urls": len(mappings),
            "with_templates": sum(1 for m in mappings if m.template),
            "api_endpoints": sum(1 for m in mappings if m.is_api),
            "with_issues": sum(1 for m in mappings if m.issues),
        },
        "by_app": {},
        "issues": [],
    }
    
    for mapping in mappings:
        if mapping.app not in report["by_app"]:
            report["by_app"][mapping.app] = []
        
        report["by_app"][mapping.app].append({
            "pattern": mapping.pattern,
            "name": mapping.name,
            "view": mapping.view,
            "template": mapping.template,
            "is_api": mapping.is_api,
        })
        
        if mapping.issues:
            report["issues"].append({
                "app": mapping.app,
                "url": mapping.name,
                "issues": mapping.issues,
            })
    
    return report


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")
    
    mappings = audit_url_mappings(project_root)
    report = generate_report(mappings)
    
    print("\n" + "=" * 60)
    print("URL MAPPING AUDIT REPORT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Total URLs: {report['summary']['total_urls']}")
    print(f"   With Templates: {report['summary']['with_templates']}")
    print(f"   API Endpoints: {report['summary']['api_endpoints']}")
    print(f"   With Issues: {report['summary']['with_issues']}")
    
    if report["issues"]:
        print(f"\n⚠️  Issues Found ({len(report['issues'])}):")
        for issue in report["issues"][:10]:
            print(f"   - [{issue['app']}] {issue['url']}: {', '.join(issue['issues'])}")
    
    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "url_map_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return 0 if not report["issues"] else 1


if __name__ == "__main__":
    sys.exit(main())
