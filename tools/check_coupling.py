"""
Lightweight coupling check: flags direct cross-app model imports.
Run: python tools/check_coupling.py
"""

from __future__ import annotations

import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
apps_dir = BASE / "apps"

pattern = re.compile(r"from\s+apps\.([a-zA-Z_]+)\.models\s+import\s+", re.MULTILINE)

def scan_file(path: Path, app_name: str):
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits = pattern.findall(text)
    bad = []
    for target in hits:
        if target != app_name and app_name not in {"admin_suite"}:
            bad.append(target)
    if bad:
        print(f"{path}: imports models from {set(bad)}")


def main():
    for app_path in apps_dir.iterdir():
        if not app_path.is_dir() or app_path.name.startswith("__"):
            continue
        app_name = app_path.name
        for py in app_path.rglob("*.py"):
            scan_file(py, app_name)


if __name__ == "__main__":
    main()
