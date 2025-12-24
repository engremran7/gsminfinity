#!/usr/bin/env python
"""
Static Files Integrity Audit Script
Verifies all {% static %} references point to existing files.

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
class StaticReference:
    """Represents a {% static %} tag in a template."""
    template_file: str
    line_number: int
    static_path: str
    exists: bool = True
    issue: str | None = None


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def get_static_files(project_root: Path) -> set[str]:
    """Get all static files in the project."""
    static_files = set()
    
    static_dirs = [
        project_root / "static",
        project_root / "staticfiles",
    ]
    
    for static_dir in static_dirs:
        if static_dir.exists():
            for file_path in static_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = file_path.relative_to(static_dir)
                    static_files.add(str(rel_path).replace("\\", "/"))
    
    return static_files


def extract_static_references(template_file: Path) -> list[StaticReference]:
    """Extract all {% static %} references from a template."""
    references = []
    
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Pattern for {% static 'path' %} or {% static "path" %}
        static_pattern = re.compile(r"\{%\s*static\s+['\"]([^'\"]+)['\"]")
        
        for i, line in enumerate(lines, 1):
            for match in static_pattern.finditer(line):
                references.append(StaticReference(
                    template_file=str(template_file),
                    line_number=i,
                    static_path=match.group(1),
                ))
                
    except Exception as e:
        print(f"Error parsing {template_file}: {e}", file=sys.stderr)
    
    return references


def detect_duplicate_static_files(project_root: Path) -> list[dict[str, Any]]:
    """Detect duplicate static files."""
    duplicates = []
    static_dir = project_root / "static"
    
    if not static_dir.exists():
        return duplicates
    
    # Group files by name
    files_by_name: dict[str, list[Path]] = {}
    
    for file_path in static_dir.rglob("*"):
        if file_path.is_file():
            name = file_path.name
            if name not in files_by_name:
                files_by_name[name] = []
            files_by_name[name].append(file_path)
    
    # Find duplicates
    for name, paths in files_by_name.items():
        if len(paths) > 1:
            # Check if they're actually different files
            sizes = [p.stat().st_size for p in paths]
            if len(set(sizes)) == 1:
                duplicates.append({
                    "type": "POTENTIAL_DUPLICATE",
                    "severity": "warning",
                    "filename": name,
                    "locations": [str(p.relative_to(static_dir)) for p in paths],
                    "message": f"File '{name}' exists in multiple locations with same size",
                })
            else:
                duplicates.append({
                    "type": "NAME_COLLISION",
                    "severity": "info",
                    "filename": name,
                    "locations": [str(p.relative_to(static_dir)) for p in paths],
                    "message": f"File '{name}' exists in multiple locations with different sizes",
                })
    
    return duplicates


def analyze_css_js_structure(project_root: Path) -> dict[str, Any]:
    """Analyze CSS and JS file structure."""
    static_dir = project_root / "static"
    
    css_files = list(static_dir.rglob("*.css"))
    js_files = list(static_dir.rglob("*.js"))
    
    return {
        "css": {
            "total": len(css_files),
            "by_directory": dict(sorted(
                ((str(f.parent.relative_to(static_dir)), 1)
                 for f in css_files),
                key=lambda x: x[0]
            )),
            "files": [str(f.relative_to(static_dir)) for f in css_files],
        },
        "js": {
            "total": len(js_files),
            "by_directory": dict(sorted(
                ((str(f.parent.relative_to(static_dir)), 1)
                 for f in js_files),
                key=lambda x: x[0]
            )),
            "files": [str(f.relative_to(static_dir)) for f in js_files],
        },
    }


def audit_static_integrity(project_root: Path) -> dict[str, Any]:
    """Audit static file references."""
    templates_dir = project_root / "templates"
    apps_dir = project_root / "apps"
    
    # Get all static files
    static_files = get_static_files(project_root)
    
    # Find all templates
    template_files = list(templates_dir.glob("**/*.html"))
    template_files.extend(apps_dir.glob("**/templates/**/*.html"))
    
    all_references: list[StaticReference] = []
    
    for template_file in template_files:
        refs = extract_static_references(template_file)
        all_references.extend(refs)
    
    # Validate references
    missing_refs = []
    for ref in all_references:
        if ref.static_path not in static_files:
            ref.exists = False
            ref.issue = f"Static file '{ref.static_path}' not found"
            missing_refs.append(ref)
    
    # Find unused static files
    referenced_paths = {r.static_path for r in all_references}
    unused_files = [f for f in static_files if f not in referenced_paths]
    
    # Get duplicates
    duplicates = detect_duplicate_static_files(project_root)
    
    # Analyze structure
    structure = analyze_css_js_structure(project_root)
    
    return {
        "summary": {
            "total_static_refs": len(all_references),
            "valid_refs": len(all_references) - len(missing_refs),
            "missing_refs": len(missing_refs),
            "total_static_files": len(static_files),
            "unused_files": len(unused_files),
            "duplicate_warnings": len(duplicates),
        },
        "missing_references": [
            {
                "file": r.template_file,
                "line": r.line_number,
                "static_path": r.static_path,
            }
            for r in missing_refs
        ],
        "unused_files": unused_files[:50],  # Limit to first 50
        "duplicates": duplicates,
        "structure": structure,
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")
    
    report = audit_static_integrity(project_root)
    
    print("\n" + "=" * 60)
    print("STATIC FILES INTEGRITY AUDIT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Total Static References: {report['summary']['total_static_refs']}")
    print(f"   Valid References: {report['summary']['valid_refs']}")
    print(f"   Missing References: {report['summary']['missing_refs']}")
    print(f"   Total Static Files: {report['summary']['total_static_files']}")
    print(f"   Unused Files: {report['summary']['unused_files']}")
    print(f"   Duplicate Warnings: {report['summary']['duplicate_warnings']}")
    
    print(f"\n📁 CSS/JS Structure:")
    print(f"   CSS Files: {report['structure']['css']['total']}")
    print(f"   JS Files: {report['structure']['js']['total']}")
    
    if report["missing_references"]:
        print(f"\n❌ Missing Static Files ({len(report['missing_references'])}):")
        for ref in report["missing_references"][:10]:
            print(f"   - {ref['static_path']}")
            print(f"     Referenced in: {ref['file']}:{ref['line']}")
    
    if report["duplicates"]:
        print(f"\n⚠️  Duplicate Warnings ({len(report['duplicates'])}):")
        for dup in report["duplicates"][:5]:
            print(f"   - {dup['filename']}: {dup['message']}")
    
    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "static_integrity_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return 0 if len(report["missing_references"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
