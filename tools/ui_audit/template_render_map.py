#!/usr/bin/env python
"""
Template Render Map Audit Script
Maps all views to their rendered templates and detects coupling issues.

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
class RenderCall:
    """Represents a render() call in a view."""
    view_name: str
    view_file: str
    line_number: int
    template: str
    is_conditional: bool = False
    context_vars: list[str] = field(default_factory=list)


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def extract_render_calls(view_file: Path) -> list[RenderCall]:
    """Extract all render() calls from a views.py file."""
    calls = []

    try:
        with open(view_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            content = "".join(lines)

        # Find all function definitions
        func_pattern = re.compile(r"def\s+(\w+)\s*\([^)]*\):", re.MULTILINE)
        class_pattern = re.compile(r"class\s+(\w+)\s*\([^)]*\):", re.MULTILINE)

        # Find all render calls
        render_pattern = re.compile(
            r"render\s*\(\s*\w+\s*,\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE
        )

        # Find template_name assignments
        template_name_pattern = re.compile(
            r"template_name\s*=\s*['\"]([^'\"]+)['\"]",
            re.MULTILINE
        )

        current_view = None
        in_class = None

        for i, line in enumerate(lines, 1):
            # Track current function/class
            func_match = func_pattern.match(line.strip())
            class_match = class_pattern.match(line.strip())

            if class_match:
                in_class = class_match.group(1)
                current_view = in_class
            elif func_match and not line.startswith(" " * 4):
                in_class = None
                current_view = func_match.group(1)
            elif func_match and in_class:
                # Method in a class
                current_view = f"{in_class}.{func_match.group(1)}"

            # Check for render calls
            render_match = render_pattern.search(line)
            if render_match and current_view:
                calls.append(RenderCall(
                    view_name=current_view,
                    view_file=str(view_file),
                    line_number=i,
                    template=render_match.group(1),
                    is_conditional="if " in "".join(lines[max(0, i-5):i]),
                ))

            # Check for template_name
            template_match = template_name_pattern.search(line)
            if template_match and current_view:
                calls.append(RenderCall(
                    view_name=current_view,
                    view_file=str(view_file),
                    line_number=i,
                    template=template_match.group(1),
                ))

    except Exception as e:
        print(f"Error parsing {view_file}: {e}", file=sys.stderr)

    return calls


def detect_coupling_issues(calls: list[RenderCall], templates_dir: Path) -> list[dict[str, Any]]:
    """Detect coupling issues between views and templates."""
    issues = []

    # Group by view
    views_templates: dict[str, list[str]] = {}
    for call in calls:
        if call.view_name not in views_templates:
            views_templates[call.view_name] = []
        if call.template not in views_templates[call.view_name]:
            views_templates[call.view_name].append(call.template)

    # Check for multiple templates per view
    for view, templates in views_templates.items():
        if len(templates) > 1:
            issues.append({
                "type": "MULTIPLE_TEMPLATES",
                "severity": "warning",
                "view": view,
                "templates": templates,
                "message": f"View renders {len(templates)} different templates",
            })

    # Check for missing templates
    for call in calls:
        template_path = templates_dir / call.template
        apps_template = templates_dir.parent / "apps" / call.template

        if not template_path.exists() and not apps_template.exists():
            # Try to find in any app's templates
            found = False
            for app_dir in (templates_dir.parent / "apps").glob("**/templates"):
                if (app_dir / call.template).exists():
                    found = True
                    break

            if not found:
                issues.append({
                    "type": "MISSING_TEMPLATE",
                    "severity": "error",
                    "view": call.view_name,
                    "template": call.template,
                    "file": call.view_file,
                    "line": call.line_number,
                    "message": f"Template '{call.template}' not found",
                })

    return issues


def audit_template_renders(project_root: Path) -> dict[str, Any]:
    """Audit all template render mappings."""
    apps_dir = project_root / "apps"
    templates_dir = project_root / "templates"

    all_calls: list[RenderCall] = []

    # Find all views.py files
    view_files = list(apps_dir.glob("**/views.py"))

    for view_file in view_files:
        calls = extract_render_calls(view_file)
        all_calls.extend(calls)

    # Detect issues
    issues = detect_coupling_issues(all_calls, templates_dir)

    # Group by app
    by_app: dict[str, list[dict]] = {}
    for call in all_calls:
        app = Path(call.view_file).parent.name
        if app not in by_app:
            by_app[app] = []
        by_app[app].append({
            "view": call.view_name,
            "template": call.template,
            "line": call.line_number,
            "conditional": call.is_conditional,
        })

    return {
        "summary": {
            "total_render_calls": len(all_calls),
            "unique_views": len(set(c.view_name for c in all_calls)),
            "unique_templates": len(set(c.template for c in all_calls)),
            "issues_found": len(issues),
        },
        "by_app": by_app,
        "issues": issues,
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")

    report = audit_template_renders(project_root)

    print("\n" + "=" * 60)
    print("TEMPLATE RENDER MAP AUDIT")
    print("=" * 60)

    print(f"\n📊 Summary:")
    print(f"   Total Render Calls: {report['summary']['total_render_calls']}")
    print(f"   Unique Views: {report['summary']['unique_views']}")
    print(f"   Unique Templates: {report['summary']['unique_templates']}")
    print(f"   Issues Found: {report['summary']['issues_found']}")

    if report["issues"]:
        print(f"\n⚠️  Issues ({len(report['issues'])}):")
        for issue in report["issues"][:10]:
            icon = "❌" if issue["severity"] == "error" else "⚠️"
            print(f"   {icon} [{issue['type']}] {issue['message']}")
            if "view" in issue:
                print(f"      View: {issue['view']}")

    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "template_render_map_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    error_count = sum(1 for i in report["issues"] if i["severity"] == "error")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
