
from __future__ import annotations

"""
Small stateless helpers live here. Avoid turning this into a grab-bag; prefer domain modules.
"""

def clamp(val, low, high):
    return max(low, min(high, val))


