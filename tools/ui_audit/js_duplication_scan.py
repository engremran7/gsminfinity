#!/usr/bin/env python
"""
JavaScript Duplication Scan Script
Detects duplicate code patterns across JavaScript files.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class JSFunction:
    """Represents a JavaScript function."""
    name: str
    file: str
    line: int
    content: str
    content_hash: str


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def extract_js_functions(js_file: Path) -> list[JSFunction]:
    """Extract functions from a JavaScript file."""
    functions = []

    try:
        with open(js_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Pattern for function declarations and expressions
        patterns = [
            # function name() {}
            re.compile(r'function\s+(\w+)\s*\([^)]*\)\s*\{', re.MULTILINE),
            # const name = function() {}
            re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{', re.MULTILINE),
            # const name = () => {}
            re.compile(r'(?:const|let|var)\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{', re.MULTILINE),
            # name: function() {}
            re.compile(r'(\w+)\s*:\s*function\s*\([^)]*\)\s*\{', re.MULTILINE),
        ]

        lines = content.split('\n')

        for pattern in patterns:
            for match in pattern.finditer(content):
                func_name = match.group(1)
                start_pos = match.start()

                # Find line number
                line_num = content[:start_pos].count('\n') + 1

                # Extract function body (simplified - just get next 50 lines)
                start_line = line_num - 1
                end_line = min(start_line + 50, len(lines))
                func_content = '\n'.join(lines[start_line:end_line])

                # Normalize for comparison
                normalized = re.sub(r'\s+', ' ', func_content).strip()
                content_hash = hashlib.md5(normalized.encode()).hexdigest()

                functions.append(JSFunction(
                    name=func_name,
                    file=str(js_file),
                    line=line_num,
                    content=func_content[:500],  # Limit content size
                    content_hash=content_hash,
                ))

    except Exception as e:
        print(f"Error parsing {js_file}: {e}", file=sys.stderr)

    return functions


def find_duplicate_functions(functions: list[JSFunction]) -> list[dict[str, Any]]:
    """Find functions with duplicate or similar content."""
    duplicates = []

    # Group by hash for exact duplicates
    by_hash: dict[str, list[JSFunction]] = defaultdict(list)
    for func in functions:
        by_hash[func.content_hash].append(func)

    for hash_val, group in by_hash.items():
        if len(group) > 1:
            duplicates.append({
                "type": "EXACT_DUPLICATE",
                "severity": "warning",
                "functions": [
                    {"name": f.name, "file": f.file, "line": f.line}
                    for f in group
                ],
                "message": f"Function '{group[0].name}' appears {len(group)} times with identical content",
            })

    return duplicates


def find_similar_functions(
    functions: list[JSFunction],
    threshold: float = 0.8
) -> list[dict[str, Any]]:
    """Find functions with similar but not identical content."""
    similar = []

    # Compare functions with same name
    by_name: dict[str, list[JSFunction]] = defaultdict(list)
    for func in functions:
        by_name[func.name].append(func)

    for name, group in by_name.items():
        if len(group) > 1:
            # Check if they're actually different
            hashes = set(f.content_hash for f in group)
            if len(hashes) > 1:
                similar.append({
                    "type": "SAME_NAME_DIFFERENT_IMPL",
                    "severity": "warning",
                    "function_name": name,
                    "locations": [
                        {"file": f.file, "line": f.line}
                        for f in group
                    ],
                    "message": f"Function '{name}' has {len(group)} different implementations",
                })

    return similar


def analyze_code_patterns(js_files: list[Path]) -> dict[str, Any]:
    """Analyze common code patterns."""
    patterns = {
        "event_listeners": 0,
        "fetch_calls": 0,
        "dom_queries": 0,
        "jquery_usage": 0,
        "async_functions": 0,
        "arrow_functions": 0,
        "class_definitions": 0,
    }

    for js_file in js_files:
        try:
            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            patterns["event_listeners"] += len(re.findall(r'addEventListener\s*\(', content))
            patterns["fetch_calls"] += len(re.findall(r'fetch\s*\(', content))
            patterns["dom_queries"] += len(re.findall(r'querySelector|getElementById|getElementsBy', content))
            patterns["jquery_usage"] += len(re.findall(r'\$\s*\(|jQuery\s*\(', content))
            patterns["async_functions"] += len(re.findall(r'async\s+function|async\s*\(', content))
            patterns["arrow_functions"] += len(re.findall(r'=>', content))
            patterns["class_definitions"] += len(re.findall(r'\bclass\s+\w+', content))

        except Exception:
            continue

    return patterns


def audit_js_duplication(project_root: Path) -> dict[str, Any]:
    """Audit JavaScript files for duplication."""
    static_dir = project_root / "static"

    # Find all JS files
    js_files = list(static_dir.glob("**/*.js"))

    # Extract functions from all files
    all_functions: list[JSFunction] = []
    for js_file in js_files:
        functions = extract_js_functions(js_file)
        all_functions.extend(functions)

    # Find duplicates
    exact_duplicates = find_duplicate_functions(all_functions)
    similar_functions = find_similar_functions(all_functions)

    # Analyze patterns
    patterns = analyze_code_patterns(js_files)

    # Calculate file sizes
    file_sizes = {}
    total_size = 0
    for js_file in js_files:
        size = js_file.stat().st_size
        file_sizes[str(js_file.relative_to(static_dir))] = size
        total_size += size

    return {
        "summary": {
            "total_js_files": len(js_files),
            "total_functions": len(all_functions),
            "exact_duplicates": len(exact_duplicates),
            "similar_functions": len(similar_functions),
            "total_size_kb": round(total_size / 1024, 2),
        },
        "code_patterns": patterns,
        "file_sizes": dict(sorted(file_sizes.items(), key=lambda x: -x[1])[:10]),
        "exact_duplicates": exact_duplicates,
        "similar_functions": similar_functions[:20],
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")

    report = audit_js_duplication(project_root)

    print("\n" + "=" * 60)
    print("JAVASCRIPT DUPLICATION AUDIT")
    print("=" * 60)

    print(f"\n📊 Summary:")
    print(f"   Total JS Files: {report['summary']['total_js_files']}")
    print(f"   Total Functions: {report['summary']['total_functions']}")
    print(f"   Exact Duplicates: {report['summary']['exact_duplicates']}")
    print(f"   Similar Functions: {report['summary']['similar_functions']}")
    print(f"   Total Size: {report['summary']['total_size_kb']} KB")

    print(f"\n📊 Code Patterns:")
    for pattern, count in report["code_patterns"].items():
        if count > 0:
            print(f"   {pattern.replace('_', ' ').title()}: {count}")

    print(f"\n📁 Largest Files:")
    for file, size in list(report["file_sizes"].items())[:5]:
        print(f"   {file}: {round(size / 1024, 2)} KB")

    if report["exact_duplicates"]:
        print(f"\n⚠️  Exact Duplicates ({len(report['exact_duplicates'])}):")
        for dup in report["exact_duplicates"][:5]:
            print(f"   {dup['message']}")
            for func in dup["functions"][:3]:
                print(f"     - {func['file']}:{func['line']}")

    if report["similar_functions"]:
        print(f"\n📋 Similar Functions ({len(report['similar_functions'])}):")
        for sim in report["similar_functions"][:5]:
            print(f"   {sim['message']}")

    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "js_duplication_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    total_issues = len(report["exact_duplicates"]) + len(report["similar_functions"])
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
