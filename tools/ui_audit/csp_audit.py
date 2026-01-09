#!/usr/bin/env python
"""
CSP Compliance Audit Script
Validates Content Security Policy compliance across templates and scripts.

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
class CSPViolation:
    """Represents a potential CSP violation."""
    file: str
    line: int
    violation_type: str
    severity: str
    code_snippet: str
    recommendation: str


def find_project_root() -> Path:
    """Find project root by looking for manage.py."""
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "manage.py").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (manage.py not found)")


def check_inline_scripts(template_file: Path) -> list[CSPViolation]:
    """Check for inline scripts without nonce."""
    violations = []

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        in_script = False
        script_start_line = 0

        for i, line in enumerate(lines, 1):
            # Check for script tags
            if "<script" in line.lower():
                # Check if it has a nonce
                has_nonce = 'nonce=' in line or 'nonce =' in line
                has_src = 'src=' in line or 'src =' in line

                if not has_src and not has_nonce:
                    # Inline script without nonce
                    violations.append(CSPViolation(
                        file=str(template_file),
                        line=i,
                        violation_type="INLINE_SCRIPT_NO_NONCE",
                        severity="error",
                        code_snippet=line.strip()[:100],
                        recommendation="Add nonce=\"{{ request.csp_nonce }}\" to inline script",
                    ))
                elif has_src and not has_nonce:
                    # External script - check if it should have nonce
                    # Note: External scripts don't need nonce if from 'self'
                    pass

    except Exception as e:
        print(f"Error checking {template_file}: {e}", file=sys.stderr)

    return violations


def check_inline_handlers(template_file: Path) -> list[CSPViolation]:
    """Check for inline event handlers (onclick, onsubmit, etc.)."""
    violations = []

    handlers = [
        "onclick", "onsubmit", "onchange", "onload", "onerror",
        "onkeyup", "onkeydown", "onkeypress", "onmouseover", "onmouseout",
        "onfocus", "onblur", "oninput", "onscroll", "onresize",
    ]

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            for handler in handlers:
                pattern = re.compile(rf'{handler}\s*=\s*["\'][^"\']*["\']', re.IGNORECASE)
                if pattern.search(line):
                    violations.append(CSPViolation(
                        file=str(template_file),
                        line=i,
                        violation_type="INLINE_HANDLER",
                        severity="error",
                        code_snippet=line.strip()[:100],
                        recommendation=f"Replace {handler} with data-* attribute and event listener in external JS",
                    ))

    except Exception:
        pass

    return violations


def check_inline_styles(template_file: Path) -> list[CSPViolation]:
    """Check for inline styles that might violate CSP."""
    violations = []

    try:
        with open(template_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Check for <style> tags without nonce
            if "<style" in line.lower():
                has_nonce = 'nonce=' in line or 'nonce =' in line
                if not has_nonce:
                    violations.append(CSPViolation(
                        file=str(template_file),
                        line=i,
                        violation_type="STYLE_TAG_NO_NONCE",
                        severity="warning",
                        code_snippet=line.strip()[:100],
                        recommendation="Add nonce=\"{{ request.csp_nonce }}\" to style tag or move to external CSS",
                    ))

    except Exception:
        pass

    return violations


def check_javascript_files(js_file: Path) -> list[CSPViolation]:
    """Check JavaScript files for CSP-incompatible patterns."""
    violations = []

    # Skip minified third-party libraries
    skip_patterns = [
        'htmx.min.js',
        'summernote-lite.min.js',
        'jquery.min.js',
        'alpine.min.js',
    ]

    if any(pattern in str(js_file) for pattern in skip_patterns):
        return violations  # Don't audit third-party minified libs

    try:
        with open(js_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments (single-line and multi-line markers)
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                continue

            # Check for eval() - but not in strings or comments
            if re.search(r'\beval\s*\(', line):
                # Make sure it's not in a string
                if not re.search(r'["\'][^"\']*eval[^"\']*["\']', line):
                    violations.append(CSPViolation(
                        file=str(js_file),
                        line=i,
                        violation_type="EVAL_USAGE",
                        severity="error",
                        code_snippet=line.strip()[:100],
                        recommendation="Replace eval() with safer alternatives",
                    ))

            # Check for new Function()
            if re.search(r'new\s+Function\s*\(', line):
                violations.append(CSPViolation(
                    file=str(js_file),
                    line=i,
                    violation_type="FUNCTION_CONSTRUCTOR",
                    severity="error",
                    code_snippet=line.strip()[:100],
                    recommendation="Replace new Function() with regular function",
                ))

            # Check for innerHTML with potential user input
            if '.innerHTML' in line and ('=' in line or '+=' in line):
                # This is informational - might be safe
                violations.append(CSPViolation(
                    file=str(js_file),
                    line=i,
                    violation_type="INNERHTML_USAGE",
                    severity="info",
                    code_snippet=line.strip()[:100],
                    recommendation="Ensure innerHTML content is sanitized or use textContent",
                ))

    except Exception:
        pass

    return violations


def check_csp_middleware(project_root: Path) -> dict[str, Any]:
    """Check CSP middleware configuration."""
    middleware_info = {
        "csp_middleware_found": False,
        "nonce_generation": False,
        "security_headers_middleware": False,
        "csp_directives": [],
    }

    # Check for CSP middleware files
    csp_middleware = project_root / "app" / "middleware" / "csp_nonce.py"
    security_middleware = project_root / "apps" / "core" / "middleware" / "security_headers.py"

    if csp_middleware.exists():
        middleware_info["csp_middleware_found"] = True
        try:
            with open(csp_middleware, "r", encoding="utf-8") as f:
                content = f.read()
            if "csp_nonce" in content:
                middleware_info["nonce_generation"] = True
        except Exception:
            pass

    if security_middleware.exists():
        middleware_info["security_headers_middleware"] = True
        try:
            with open(security_middleware, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract CSP directives
            directives = re.findall(r"(script-src|style-src|default-src|img-src|connect-src|frame-src)[^;]+", content)
            middleware_info["csp_directives"] = directives
        except Exception:
            pass

    return middleware_info


def audit_csp(project_root: Path) -> dict[str, Any]:
    """Audit CSP compliance."""
    templates_dir = project_root / "templates"
    apps_dir = project_root / "apps"
    static_dir = project_root / "static"

    # Find all files to check
    template_files = list(templates_dir.glob("**/*.html"))
    template_files.extend(apps_dir.glob("**/templates/**/*.html"))

    js_files = list(static_dir.glob("**/*.js"))

    all_violations: list[CSPViolation] = []

    # Check templates
    for template in template_files:
        all_violations.extend(check_inline_scripts(template))
        all_violations.extend(check_inline_handlers(template))
        all_violations.extend(check_inline_styles(template))

    # Check JavaScript files
    for js_file in js_files:
        all_violations.extend(check_javascript_files(js_file))

    # Check middleware
    middleware_info = check_csp_middleware(project_root)

    # Categorize violations
    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {"error": 0, "warning": 0, "info": 0}

    for v in all_violations:
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        by_severity[v.severity] += 1

    return {
        "summary": {
            "total_violations": len(all_violations),
            "errors": by_severity["error"],
            "warnings": by_severity["warning"],
            "info": by_severity["info"],
            "templates_checked": len(template_files),
            "js_files_checked": len(js_files),
        },
        "middleware": middleware_info,
        "by_violation_type": by_type,
        "violations": [
            {
                "file": v.file,
                "line": v.line,
                "type": v.violation_type,
                "severity": v.severity,
                "snippet": v.code_snippet,
                "recommendation": v.recommendation,
            }
            for v in all_violations
        ],
    }


def main():
    """Main entry point."""
    project_root = find_project_root()
    print(f"📍 Project root: {project_root}")

    report = audit_csp(project_root)

    print("\n" + "=" * 60)
    print("CSP COMPLIANCE AUDIT")
    print("=" * 60)

    print(f"\n📊 Summary:")
    print(f"   Total Violations: {report['summary']['total_violations']}")
    print(f"   Errors: {report['summary']['errors']}")
    print(f"   Warnings: {report['summary']['warnings']}")
    print(f"   Info: {report['summary']['info']}")
    print(f"   Templates Checked: {report['summary']['templates_checked']}")
    print(f"   JS Files Checked: {report['summary']['js_files_checked']}")

    print(f"\n🔒 Middleware Status:")
    print(f"   CSP Middleware: {'✅' if report['middleware']['csp_middleware_found'] else '❌'}")
    print(f"   Nonce Generation: {'✅' if report['middleware']['nonce_generation'] else '❌'}")
    print(f"   Security Headers: {'✅' if report['middleware']['security_headers_middleware'] else '❌'}")

    if report["by_violation_type"]:
        print(f"\n📊 Violations by Type:")
        for vtype, count in sorted(report["by_violation_type"].items(), key=lambda x: -x[1]):
            print(f"   {vtype}: {count}")

    if report["violations"]:
        print(f"\n❌ Top Violations:")
        for v in report["violations"][:10]:
            icon = "❌" if v["severity"] == "error" else "⚠️" if v["severity"] == "warning" else "ℹ️"
            print(f"   {icon} [{v['type']}] {v['file']}:{v['line']}")
            print(f"      {v['recommendation']}")

    # Save detailed report
    report_file = project_root / "tools" / "ui_audit" / "csp_audit_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_file}")

    return 0 if report["summary"]["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
