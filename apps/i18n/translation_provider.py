from __future__ import annotations

import logging
from typing import List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class BaseTranslator:
    def translate(self, texts: List[str], target: str, source: Optional[str] = None) -> List[str]:
        raise NotImplementedError


class DummyTranslator(BaseTranslator):
    def translate(self, texts: List[str], target: str, source: Optional[str] = None) -> List[str]:
        # No-op: returns source text
        return texts


class DeepLTranslator(BaseTranslator):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = getattr(settings, "DEEPL_ENDPOINT", "https://api-free.deepl.com/v2/translate")

    def translate(self, texts: List[str], target: str, source: Optional[str] = None) -> List[str]:
        params = {"target_lang": target.upper()}
        if source:
            params["source_lang"] = source.upper()
        translated: List[str] = []
        for text in texts:
            try:
                resp = requests.post(
                    self.endpoint,
                    data={**params, "text": text},
                    timeout=10,
                    headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
                tr = data.get("translations", [])
                if tr:
                    translated.append(tr[0].get("text", text))
                else:
                    translated.append(text)
            except Exception as exc:
                logger.warning("DeepL translation failed: %s", exc)
                translated.append(text)
        return translated


class ArgosTranslator(BaseTranslator):
    """
    Offline/local translation using argostranslate if installed.
    """

    def __init__(self):
        try:
            import argostranslate.package  # type: ignore
            import argostranslate.translate  # type: ignore
        except Exception as exc:
            raise ImportError("argostranslate not installed") from exc
        self.argos = __import__("argostranslate.translate").translate

    def translate(self, texts: List[str], target: str, source: Optional[str] = None) -> List[str]:
        translated: List[str] = []
        for text in texts:
            try:
                tr = self.argos.translate(text, from_code=source or "en", to_code=target)
                translated.append(tr)
            except Exception as exc:
                logger.warning("Argos translation failed: %s", exc)
                translated.append(text)
        return translated


def get_translator() -> BaseTranslator:
    provider = getattr(settings, "TRANSLATION_PROVIDER", "").lower()
    api_key = getattr(settings, "TRANSLATION_API_KEY", None)
    if provider == "deepl" and api_key:
        return DeepLTranslator(api_key)
    if provider == "argos":
        try:
            return ArgosTranslator()
        except Exception as exc:
            logger.warning("Argos translator unavailable: %s", exc)
    # Fallback dummy
    return DummyTranslator()
