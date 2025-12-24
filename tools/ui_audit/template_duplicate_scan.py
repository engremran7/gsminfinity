#!/usr/bin/env python
"""
Template Duplicate Detection Script
Finds duplicate or near-duplicate template content.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


@dataclass
class TemplateInfo:
    """Information about a template file."""
    path: str
    content_hash: str
    normalized_content: str
    size: int
    extends: str | None
    includes: list[str]
    blocks: list[str]


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def normalize_template(content: str) -> str:
    """Normalize template content for comparison."""
    # Remove comments
    content = re.sub(r"\{#.*?#\}", "", content, flags=re.DOTALL)
    # Normalize whitespace
    content = re.sub(r"\s+", " ", content)
    # Remove leading/trailing whitespace
    content = content.strip()
    return content


def extract_template_info(template_file: Path) -> TemplateInfo:
    """Extract information from a template file."""
    try:
        with open(template_file, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        content = ""
    
    normalized = normalize_template(content)
    content_hash = hashlib.md5(normalized.encode()).hexdigest()
    
    # Extract extends
    extends_match = re.search(r"\{%\s*extends\s+['\"]([^'\"]+)['\"]", content)
    extends = extends_match.group(1) if extends_match else None
    
    # Extract includes
    includes = re.findall(r"\{%\s*include\s+['\"]([^'\"]+)['\"]", content)
    
    # Extract block names
    blocks = re.findall(r"\{%\s*block\s+(\w+)", content)
    
    return TemplateInfo(
        path=str(template_file),
        content_hash=content_hash,
        normalized_content=normalized,
        size=len(content),
        extends=extends,
        includes=includes,
        blocks=blocks,
    )


def find_exact_duplicates(templates: list[TemplateInfo]) -> list[dict[str, Any]]:
    """Find templates with identical content."""
    duplicates = []
    
    # Group by hash
    by_hash: dict[str, list[TemplateInfo]] = defaultdict(list)
    for t in templates:
        by_hash[t.content_hash].append(t)
    
    # Find duplicates
    for hash_val, group in by_hash.items():
        if len(group) > 1:
            duplicates.append({
                "type": "EXACT_DUPLICATE",
                "severity": "warning",
                "files": [t.path for t in group],
                "size": group[0].size,
                "message": f"{len(group)} templates have identical content",
            })
    
    return duplicates


def find_similar_templates(
    templates: list[TemplateInfo], 
    threshold: float = 0.85
) -> list[dict[str, Any]]:
    """Find templates with similar content."""
    similar = []
    
    # Only compare templates of similar size and different content
    for i, t1 in enumerate(templates):
        for t2 in templates[i + 1:]:
            if t1.content_hash == t2.content_hash:
                continue  # Already found as exact duplicate
            
            # Skip if sizes are very different
            size_ratio = min(t1.size, t2.size) / max(t1.size, t2.size) if max(t1.size, t2.size) > 0 else 0
            if size_ratio < 0.5:
                continue
            
            # Compare content
            ratio = SequenceMatcher(
                None, 
                t1.normalized_content[:5000],  # Limit for performance
                t2.normalized_content[:5000]
            ).ratio()
            
            if ratio >= threshold:
                similar.append({
                    "type": "SIMILAR_CONTENT",
                    "severity": "info",
                    "files": [t1.path, t2.path],
                    "similarity": round(ratio * 100, 1),
                    "message": f"Templates are {round(ratio * 100, 1)}% similar",
                })
    
    return similar


def analyze_template_hierarchy(templates: list[TemplateInfo]) -> dict[str, Any]:
    """Analyze template inheritance hierarchy."""
    hierarchy = {
        "base_templates": [],
        "extends_count": defaultdict(int),
        "orphan_templates": [],
    }
    
    # Find base templates (not extending anything)
    for t in templates:
        if t.extends is None:
            hierarchy["base_templates"].append(t.path)
        else:
            hierarchy["extends_count"][t.extends] += 1
    
    # Find orphans (extending non-existent templates)
    template_paths = {Path(t.path).name for t in templates}
    for t in templates:
        if t.extends and Path(t.extends).name not in template_paths:
            # Check if it's a Django admin template
            if not t.extends.startswith("admin/"):
                hierarchy["orphan_templates"].append({
                    "template": t.path,
                    "extends": t.extends,
                })
    
    return hierarchy


def audit_template_duplicates(project_root: Path) -> dict[str, Any]:
    """Audit templates for duplicates."""
    templates_dir = project_root / "templates"
    apps_dir = project_root / "apps"
    
    # Find all templates
    template_files = list(templates_dir.glob("**/*.html"))
    template_files.extend(apps_dir.glob("**/templates/**/*.html"))
    
    # Extract info from each template
    templates = [extract_template_info(f) for f in template_files]
    
    # Find duplicates
    exact_duplicates = find_exact_duplicates(templates)
    similar_templates = find_similar_templates(templates)
    
    # Analyze hierarchy
    hierarchy = analyze_template_hierarchy(templates)
    
    return {
        "summary": {
            "total_templates": len(templates),
            "exact_duplicates": len(exact_duplicates),
            "similar_templates": len(similar_templates),
            "base_templates": len(hierarchy["base_templates"]),
            "orphan_templates": len(hierarchy["orphan_templates"]),
        },
        "exact_duplicates": exact_duplicates,
        "similar_templates": similar_templates[:20],  # Limit output
        "hierarchy": {
            "base_templates": hierarchy["base_templates"],
            "most_extended": dict(sorted(
                hierarchy["extends_count"].items(),
                key=lambda x: -x[1]
            )[:10]),
            "orphan_templates": hierarchy["orphan_templates"],
        },
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")
    
    report = audit_template_duplicates(project_root)
    
    print("\n" + "=" * 60)
    print("TEMPLATE DUPLICATE AUDIT")
    print("=" * 60)
    
    print(f"\n📊 Summary:")
    print(f"   Total Templates: {report['summary']['total_templates']}")
    print(f"   Exact Duplicates: {report['summary']['exact_duplicates']}")
    print(f"   Similar Templates: {report['summary']['similar_templates']}")
    print(f"   Base Templates: {report['summary']['base_templates']}")
    print(f"   Orphan Templates: {report['summary']['orphan_templates']}")
    
    if report["exact_duplicates"]:
        print(f"\n⚠️  Exact Duplicates ({len(report['exact_duplicates'])}):")
        for dup in report["exact_duplicates"][:5]:
            print(f"   Files: {len(dup['files'])} templates with identical content")
            for f in dup["files"][:3]:
                print(f"     - {f}")
    
    if report["similar_templates"]:
        print(f"\n📋 Similar Templates ({len(report['similar_templates'])}):")
        for sim in report["similar_templates"][:5]:
            print(f"   {sim['similarity']}% similar:")
            for f in sim["files"]:
                print(f"     - {f}")
    
    print(f"\n📊 Inheritance Hierarchy:")
    print(f"   Most Extended Templates:")
    for template, count in list(report["hierarchy"]["most_extended"].items())[:5]:
        print(f"     - {template}: {count} extensions")
    
    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "template_duplicate_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    return 0 if len(report["exact_duplicates"]) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
