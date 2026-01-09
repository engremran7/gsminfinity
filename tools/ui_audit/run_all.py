#!/usr/bin/env python
"""
UI Audit Runner
Runs all UI audit scripts and generates a comprehensive report.

Part of GSM Infinity Enterprise UI Audit Suite
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
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


AUDIT_SCRIPTS = [
    ("url_map.py", "URL Mapping Audit"),
    ("template_render_map.py", "Template Render Map"),
    ("template_link_integrity.py", "Template Link Integrity"),
    ("static_integrity.py", "Static Files Integrity"),
    ("template_duplicate_scan.py", "Template Duplicates"),
    ("tailwind_audit.py", "Tailwind CSS Audit"),
    ("htmx_audit.py", "HTMX Audit"),
    ("csp_audit.py", "CSP Compliance Audit"),
    ("js_duplication_scan.py", "JavaScript Duplication"),
]


def run_audit_script(script_path: Path, name: str) -> dict[str, Any]:
    """Run a single audit script and capture output."""
    result = {
        "name": name,
        "script": script_path.name,
        "status": "unknown",
        "exit_code": -1,
        "output": "",
        "error": "",
    }

    try:
        process = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=script_path.parent.parent.parent,
        )

        result["exit_code"] = process.returncode
        result["output"] = process.stdout
        result["error"] = process.stderr
        result["status"] = "passed" if process.returncode == 0 else "failed"

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["error"] = "Script timed out after 120 seconds"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


def generate_summary_report(results: list[dict[str, Any]], project_root: Path) -> dict[str, Any]:
    """Generate a summary report from all audit results."""
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    errors = sum(1 for r in results if r["status"] in ["error", "timeout"])

    # Load individual reports
    reports_dir = project_root / "tools" / "ui_audit"
    individual_summaries = {}

    report_files = [
        ("url_map_report.json", "url_map"),
        ("template_render_map_report.json", "template_render"),
        ("template_link_integrity_report.json", "link_integrity"),
        ("static_integrity_report.json", "static_integrity"),
        ("template_duplicate_report.json", "duplicates"),
        ("tailwind_audit_report.json", "tailwind"),
        ("htmx_audit_report.json", "htmx"),
        ("csp_audit_report.json", "csp"),
        ("js_duplication_report.json", "js_duplication"),
    ]

    for filename, key in report_files:
        report_path = reports_dir / filename
        if report_path.exists():
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                individual_summaries[key] = data.get("summary", {})
            except Exception:
                pass

    return {
        "meta": {
            "generated_at": datetime.now().isoformat(),
            "project_root": str(project_root),
            "audit_version": "1.0.0",
        },
        "overall": {
            "total_audits": len(results),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "health_score": round((passed / len(results)) * 100, 1) if results else 0,
        },
        "audit_results": [
            {
                "name": r["name"],
                "status": r["status"],
                "exit_code": r["exit_code"],
            }
            for r in results
        ],
        "individual_summaries": individual_summaries,
    }


def print_report(summary: dict[str, Any]):
    """Print a formatted report to console."""
    print("\n" + "=" * 70)
    print("  GSM INFINITY - ENTERPRISE UI AUDIT REPORT")
    print("=" * 70)
    print(f"\n📅 Generated: {summary['meta']['generated_at']}")
    print(f"📁 Project: {summary['meta']['project_root']}")

    print("\n" + "-" * 70)
    print("  OVERALL HEALTH")
    print("-" * 70)

    health = summary["overall"]["health_score"]
    health_icon = "🟢" if health >= 80 else "🟡" if health >= 60 else "🔴"

    print(f"\n{health_icon} Health Score: {health}%")
    print(f"   ✅ Passed: {summary['overall']['passed']}")
    print(f"   ❌ Failed: {summary['overall']['failed']}")
    print(f"   ⚠️  Errors: {summary['overall']['errors']}")

    print("\n" + "-" * 70)
    print("  AUDIT RESULTS")
    print("-" * 70)

    for result in summary["audit_results"]:
        icon = "✅" if result["status"] == "passed" else "❌" if result["status"] == "failed" else "⚠️"
        print(f"   {icon} {result['name']}")

    print("\n" + "-" * 70)
    print("  KEY METRICS")
    print("-" * 70)

    summaries = summary.get("individual_summaries", {})

    if "url_map" in summaries:
        s = summaries["url_map"]
        print(f"\n📍 URL Mapping:")
        print(f"   Total URLs: {s.get('total_urls', 'N/A')}")
        print(f"   With Issues: {s.get('with_issues', 'N/A')}")

    if "static_integrity" in summaries:
        s = summaries["static_integrity"]
        print(f"\n📁 Static Files:")
        print(f"   Total Files: {s.get('total_static_files', 'N/A')}")
        print(f"   Missing Refs: {s.get('missing_refs', 'N/A')}")
        print(f"   Unused Files: {s.get('unused_files', 'N/A')}")

    if "csp" in summaries:
        s = summaries["csp"]
        print(f"\n🔒 CSP Compliance:")
        print(f"   Violations: {s.get('total_violations', 'N/A')}")
        print(f"   Errors: {s.get('errors', 'N/A')}")

    if "tailwind" in summaries:
        s = summaries["tailwind"]
        print(f"\n🎨 Tailwind CSS:")
        print(f"   Templates: {s.get('templates_scanned', 'N/A')}")
        print(f"   Unique Classes: {s.get('unique_classes', 'N/A')}")

    if "htmx" in summaries:
        s = summaries["htmx"]
        print(f"\n⚡ HTMX:")
        print(f"   Usages: {s.get('total_usages', 'N/A')}")
        print(f"   Endpoints: {s.get('unique_endpoints', 'N/A')}")

    print("\n" + "=" * 70)
    print("  END OF REPORT")
    print("=" * 70 + "\n")


def main():
    """Main entry point."""
    project_root = find_project_root()
    scripts_dir = project_root / "tools" / "ui_audit"

    print("🚀 Starting GSM Infinity UI Audit Suite...")
    print(f"📁 Project: {project_root}")
    print(f"📂 Scripts: {scripts_dir}")
    print()

    results = []

    for script_name, display_name in AUDIT_SCRIPTS:
        script_path = scripts_dir / script_name

        if not script_path.exists():
            print(f"⚠️  Script not found: {script_name}")
            results.append({
                "name": display_name,
                "script": script_name,
                "status": "missing",
                "exit_code": -1,
                "output": "",
                "error": "Script file not found",
            })
            continue

        print(f"▶️  Running: {display_name}...")
        result = run_audit_script(script_path, display_name)
        results.append(result)

        icon = "✅" if result["status"] == "passed" else "❌" if result["status"] == "failed" else "⚠️"
        print(f"   {icon} {result['status'].upper()}")

    # Generate summary
    summary = generate_summary_report(results, project_root)

    # Save summary report
    summary_file = scripts_dir / "ui_audit_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Print report
    print_report(summary)

    print(f"📄 Summary saved to: {summary_file}")

    # Exit with appropriate code
    if summary["overall"]["health_score"] < 60:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
