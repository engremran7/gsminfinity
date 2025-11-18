# apps/common/utils.py
import hashlib
def short_hash(value: str, length:int=10):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]
