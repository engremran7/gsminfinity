#!/usr/bin/env python
"""
Tailwind CSS Audit Script
Validates Tailwind configuration and usage patterns.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def parse_tailwind_config(config_file: Path) -> dict[str, Any]:
    """Parse Tailwind config file for analysis."""
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract content paths
        content_match = re.search(r"content:\s*\[(.*?)\]", content, re.DOTALL)
        content_paths = []
        if content_match:
            content_paths = re.findall(r"['\"]([^'\"]+)['\"]", content_match.group(1))

        # Extract plugins
        plugins_match = re.search(r"plugins:\s*\[(.*?)\]", content, re.DOTALL)
        plugins = []
        if plugins_match:
            plugins = re.findall(r"require\(['\"]([^'\"]+)['\"]\)", plugins_match.group(1))

        # Check for custom colors
        has_custom_colors = "colors:" in content

        # Check for custom utilities
        has_custom_utilities = "addUtilities" in content or "addComponents" in content

        return {
            "file": str(config_file),
            "content_paths": content_paths,
            "plugins": plugins,
            "has_custom_colors": has_custom_colors,
            "has_custom_utilities": has_custom_utilities,
            "file_size": len(content),
        }
    except Exception as e:
        return {"error": str(e)}


def extract_tailwind_classes(content: str) -> list[str]:
    """Extract Tailwind-like classes from HTML content."""
    # Look for class attributes
    class_pattern = re.compile(r'class\s*=\s*["\']([^"\']+)["\']')

    all_classes = []
    for match in class_pattern.finditer(content):
        classes = match.group(1).split()
        all_classes.extend(classes)

    return all_classes


def categorize_tailwind_class(cls: str) -> str:
    """Categorize a Tailwind class."""
    prefixes = {
        "text-": "typography",
        "font-": "typography",
        "bg-": "background",
        "border": "border",
        "rounded": "border-radius",
        "p-": "padding",
        "px-": "padding",
        "py-": "padding",
        "pt-": "padding",
        "pb-": "padding",
        "pl-": "padding",
        "pr-": "padding",
        "m-": "margin",
        "mx-": "margin",
        "my-": "margin",
        "mt-": "margin",
        "mb-": "margin",
        "ml-": "margin",
        "mr-": "margin",
        "flex": "flexbox",
        "grid": "grid",
        "w-": "width",
        "h-": "height",
        "min-": "sizing",
        "max-": "sizing",
        "gap-": "gap",
        "space-": "spacing",
        "hover:": "interaction",
        "focus:": "interaction",
        "dark:": "dark-mode",
        "sm:": "responsive",
        "md:": "responsive",
        "lg:": "responsive",
        "xl:": "responsive",
        "2xl:": "responsive",
        "animate-": "animation",
        "transition": "animation",
        "shadow": "effects",
        "opacity": "effects",
        "z-": "z-index",
        "absolute": "position",
        "relative": "position",
        "fixed": "position",
        "sticky": "position",
    }

    for prefix, category in prefixes.items():
        if cls.startswith(prefix):
            return category

    return "other"


def detect_tailwind_issues(templates: list[Path], config: dict) -> list[dict[str, Any]]:
    """Detect potential Tailwind usage issues."""
    issues = []
    all_classes: list[str] = []

    for template in templates:
        try:
            with open(template, "r", encoding="utf-8") as f:
                content = f.read()
            classes = extract_tailwind_classes(content)
            all_classes.extend(classes)

            # Check for inline styles (anti-pattern with Tailwind)
            inline_style_count = len(re.findall(r'style\s*=\s*["\']', content))
            if inline_style_count > 3:
                issues.append({
                    "type": "INLINE_STYLES",
                    "severity": "warning",
                    "file": str(template),
                    "count": inline_style_count,
                    "message": f"Template has {inline_style_count} inline styles - prefer Tailwind classes",
                })

            # Check for very long class strings (potential complexity)
            for match in re.finditer(r'class\s*=\s*["\']([^"\']+)["\']', content):
                class_list = match.group(1)
                if len(class_list.split()) > 15:
                    issues.append({
                        "type": "COMPLEX_CLASS_STRING",
                        "severity": "info",
                        "file": str(template),
                        "class_count": len(class_list.split()),
                        "message": "Consider extracting to a component",
                    })

        except Exception:
            continue

    # Check for duplicate class combinations
    class_counter = Counter(all_classes)

    # Find non-standard classes (potential typos or custom classes)
    standard_prefixes = [
        "text-", "bg-", "border", "rounded", "p-", "m-", "flex", "grid",
        "w-", "h-", "gap-", "space-", "hover:", "focus:", "dark:", "sm:",
        "md:", "lg:", "xl:", "2xl:", "animate-", "transition", "shadow",
        "opacity", "z-", "absolute", "relative", "fixed", "sticky", "hidden",
        "block", "inline", "overflow", "cursor", "items-", "justify-",
        "self-", "order-", "col-", "row-", "top-", "bottom-", "left-",
        "right-", "inset-", "transform", "scale-", "rotate-", "translate-",
        "skew-", "origin-", "font-", "tracking-", "leading-", "list-",
        "placeholder-", "decoration-", "underline", "line-through",
        "no-underline", "capitalize", "uppercase", "lowercase", "normal-case",
        "truncate", "break-", "whitespace-", "align-", "table-", "aspect-",
        "object-", "float-", "clear-", "isolate", "mix-blend-", "bg-blend-",
        "filter", "blur-", "brightness-", "contrast-", "drop-shadow-",
        "grayscale", "hue-rotate-", "invert", "saturate-", "sepia",
        "backdrop-", "ring", "divide-", "sr-only", "not-sr-only",
        "appearance-", "outline-", "resize", "scroll-", "snap-", "touch-",
        "select-", "will-change-", "fill-", "stroke-",
        # Custom classes from config
        "admin", "glassmorphism", "security-", "accent", "primary",
        "btn", "card", "chip", "auth-",
    ]

    unknown_classes = []
    for cls, count in class_counter.items():
        if not any(cls.startswith(prefix) or cls == prefix.rstrip("-")
                   for prefix in standard_prefixes):
            # Might be a custom class
            if count > 2:  # Only flag if used multiple times
                unknown_classes.append({"class": cls, "count": count})

    if unknown_classes:
        issues.append({
            "type": "UNKNOWN_CLASSES",
            "severity": "info",
            "classes": unknown_classes[:20],
            "message": f"Found {len(unknown_classes)} potentially non-Tailwind classes",
        })

    return issues


def audit_tailwind(project_root: Path) -> dict[str, Any]:
    """Audit Tailwind configuration and usage."""
    # Find Tailwind configs
    configs = []
    for config_name in ["tailwind.config.js", "tailwind.config.enterprise.js"]:
        config_path = project_root / config_name
        if config_path.exists():
            configs.append(parse_tailwind_config(config_path))

    # Find all templates
    templates = list((project_root / "templates").glob("**/*.html"))
    templates.extend((project_root / "apps").glob("**/templates/**/*.html"))

    # Extract and analyze classes
    all_classes: list[str] = []
    for template in templates:
        try:
            with open(template, "r", encoding="utf-8") as f:
                classes = extract_tailwind_classes(f.read())
                all_classes.extend(classes)
        except Exception:
            continue

    # Categorize classes
    category_counts: dict[str, int] = defaultdict(int)
    for cls in all_classes:
        category = categorize_tailwind_class(cls)
        category_counts[category] += 1

    # Detect issues
    issues = detect_tailwind_issues(templates, configs[0] if configs else {})

    # Check for config drift
    config_drift_issues = []
    if len(configs) > 1:
        config_drift_issues.append({
            "type": "MULTIPLE_CONFIGS",
            "severity": "warning",
            "files": [c.get("file") for c in configs],
            "message": "Multiple Tailwind configs found - potential drift risk",
        })

    return {
        "summary": {
            "config_files": len(configs),
            "templates_scanned": len(templates),
            "total_class_usages": len(all_classes),
            "unique_classes": len(set(all_classes)),
            "issues_found": len(issues) + len(config_drift_issues),
        },
        "configs": configs,
        "class_categories": dict(sorted(
            category_counts.items(),
            key=lambda x: -x[1]
        )),
        "most_used_classes": dict(Counter(all_classes).most_common(20)),
        "issues": issues + config_drift_issues,
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")

    report = audit_tailwind(project_root)

    print("\n" + "=" * 60)
    print("TAILWIND CSS AUDIT")
    print("=" * 60)

    print(f"\n📊 Summary:")
    print(f"   Config Files: {report['summary']['config_files']}")
    print(f"   Templates Scanned: {report['summary']['templates_scanned']}")
    print(f"   Total Class Usages: {report['summary']['total_class_usages']}")
    print(f"   Unique Classes: {report['summary']['unique_classes']}")
    print(f"   Issues Found: {report['summary']['issues_found']}")

    print(f"\n📁 Class Categories:")
    for category, count in list(report["class_categories"].items())[:10]:
        print(f"   {category}: {count}")

    print(f"\n🔝 Most Used Classes:")
    for cls, count in list(report["most_used_classes"].items())[:10]:
        print(f"   {cls}: {count}")

    if report["issues"]:
        print(f"\n⚠️  Issues ({len(report['issues'])}):")
        for issue in report["issues"][:10]:
            icon = "❌" if issue["severity"] == "error" else "⚠️" if issue["severity"] == "warning" else "ℹ️"
            print(f"   {icon} [{issue['type']}] {issue['message']}")

    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "tailwind_audit_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    error_count = sum(1 for i in report["issues"] if i.get("severity") == "error")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
