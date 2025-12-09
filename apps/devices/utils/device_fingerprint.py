from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class OSInfo:
    name: str
    version: str


def parse_os_from_ua(ua: str) -> OSInfo:
    ua = ua or ""
    if "Windows NT" in ua:
        m = re.search(r"Windows NT ([0-9.]+)", ua)
        version = m.group(1) if m else ""
        return OSInfo("Windows", version)
    if "Mac OS X" in ua:
        m = re.search(r"Mac OS X ([0-9_\\.]+)", ua)
        version = m.group(1).replace("_", ".") if m else ""
        return OSInfo("macOS", version)
    if "Android" in ua:
        m = re.search(r"Android ([0-9.]+)", ua)
        version = m.group(1) if m else ""
        return OSInfo("Android", version)
    if "iPhone OS" in ua or "iPad; CPU OS" in ua:
        m = re.search(r"OS ([0-9_]+) like Mac OS X", ua)
        version = m.group(1).replace("_", ".") if m else ""
        return OSInfo("iOS", version)
    if "Linux" in ua:
        return OSInfo("Linux", "")
    return OSInfo("Unknown", "")


def make_os_fingerprint(user_id: int, ua: str, payload: Dict[str, str] | None) -> Tuple[str, OSInfo]:
    p = payload or {}
    os_info = parse_os_from_ua(ua or "")
    stable_raw = "|".join(
        [
            str(user_id),
            os_info.name,
            os_info.version,
            str(p.get("screen", "")),
            str(p.get("pixel_ratio", "")),
            str(p.get("timezone", "")),
            str(p.get("cores", "")),
            str(p.get("device_memory", "")),
            str(p.get("touch_points", "")),
            str(p.get("languages", "")),
            str(p.get("gpu_vendor", "")),
            str(p.get("gpu_renderer", "")),
        ]
    )
    fingerprint = hashlib.sha256(stable_raw.encode("utf-8")).hexdigest()
    return fingerprint, os_info
