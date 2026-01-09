"""
Firmware AI Client - Integrates with core AI infrastructure for firmware analysis.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.cache import cache

from .constants import MAIN_CATEGORIES, MODIFIED_SUBTYPES

logger = logging.getLogger(__name__)

# Try to import core AI client
try:
    from apps.core.ai_client import (
        AICircuitBreaker,
        AiClientError,
        AIRateLimiter,
        _call_openai_response,
        _load_config,
    )
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    AiClientError = RuntimeError


class AIClient:
    """
    Firmware analysis AI client using the core AI infrastructure.
    Provides firmware classification, brand/model detection, and schema proposals.
    """

    CATEGORY_NAMES = {k: v for k, v in MAIN_CATEGORIES}

    def __init__(self):
        self.rate_limiter = AIRateLimiter(requests_per_minute=30) if AI_AVAILABLE else None
        self.circuit_breaker = AICircuitBreaker(failure_threshold=3, recovery_timeout=180) if AI_AVAILABLE else None

    def analyze_firmware(self, file_path: str, password: str | None = None) -> dict:
        """
        Analyze a firmware file to extract metadata and classify it.
        
        Args:
            file_path: Path to the firmware file
            password: Optional password for encrypted archives
            
        Returns:
            Dict with brand, model, variant, category, subtype, chipset, partitions, metadata
        """
        default_result = {
            "brand": "",
            "model": "",
            "variant": "",
            "category": None,
            "subtype": None,
            "chipset": "",
            "partitions": [],
            "metadata": {},
        }

        if not file_path or not Path(file_path).exists():
            logger.warning(f"Firmware file not found: {file_path}")
            return default_result

        filename = Path(file_path).name
        file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0

        # Try pattern-based analysis first (fast, no API call)
        pattern_result = self._analyze_by_patterns(filename)

        # If we got high confidence from patterns, return early
        if pattern_result.get("confidence", 0) >= 0.8:
            logger.info(f"Pattern-based analysis sufficient for: {filename}")
            return {**default_result, **pattern_result, "metadata": {"source": "pattern_analysis"}}

        # Use AI for deeper analysis if available and enabled
        if AI_AVAILABLE and getattr(settings, 'AI_OPENAI_API_KEY', None):
            try:
                ai_result = self._analyze_with_ai(filename, file_size, password)
                if ai_result:
                    # Merge pattern results with AI results, AI takes precedence
                    return {**default_result, **pattern_result, **ai_result, "metadata": {"source": "ai_analysis"}}
            except AiClientError as e:
                logger.warning(f"AI analysis failed, using pattern results: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in AI analysis: {e}")

        return {**default_result, **pattern_result, "metadata": {"source": "pattern_analysis"}}

    def _analyze_by_patterns(self, filename: str) -> dict:
        """Pattern-based firmware analysis for common naming conventions."""
        result = {"confidence": 0.0}
        filename_lower = filename.lower()

        # Brand detection patterns
        brand_patterns = {
            "samsung": [r"sm[-_]?[a-z]\d{3}", r"samsung", r"galaxy"],
            "xiaomi": [r"xiaomi", r"redmi", r"poco", r"miui", r"mi[-_]?\d"],
            "oppo": [r"oppo", r"cph\d{4}", r"realme"],
            "vivo": [r"vivo", r"pd\d{4}", r"iqoo"],
            "huawei": [r"huawei", r"hw[-_]", r"honor", r"emui"],
            "oneplus": [r"oneplus", r"op\d{4}"],
            "motorola": [r"motorola", r"moto[-_]", r"xt\d{4}"],
            "nokia": [r"nokia", r"ta[-_]?\d{4}"],
            "lg": [r"lg[-_]?[a-z]\d{3}", r"lgm[-_]"],
            "sony": [r"sony", r"xperia", r"xq[-_]"],
            "google": [r"pixel", r"google", r"oriole", r"raven", r"redfin"],
            "apple": [r"iphone", r"ipad", r"apple", r"ios[-_]\d"],
            "zte": [r"zte", r"blade"],
            "lenovo": [r"lenovo", r"tb[-_]?\d"],
            "tecno": [r"tecno", r"camon", r"spark"],
            "infinix": [r"infinix", r"hot[-_]?\d", r"note[-_]?\d"],
            "itel": [r"itel"],
        }

        for brand, patterns in brand_patterns.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower):
                    result["brand"] = brand.capitalize()
                    result["confidence"] = max(result["confidence"], 0.5)
                    break
            if "brand" in result:
                break

        # Model detection from common patterns
        model_patterns = [
            r"(sm[-_]?[a-z]\d{3}[a-z]?)",  # Samsung SM-XXXX
            r"(cph\d{4})",                   # OPPO CPH
            r"(rmx\d{4})",                   # Realme
            r"(ta[-_]?\d{4})",               # Nokia
            r"(xt\d{4})",                    # Motorola
            r"(v\d{4})",                     # Vivo
            r"(kb\d{4})",                    # Various
        ]

        for pattern in model_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                result["model"] = match.group(1).upper()
                result["confidence"] = max(result["confidence"], 0.6)
                break

        # Category detection
        if any(kw in filename_lower for kw in ["official", "stock", "full_ota", "baseband"]):
            result["category"] = "official"
            result["confidence"] = max(result["confidence"], 0.7)
        elif any(kw in filename_lower for kw in ["engineering", "eng_", "userdebug", "test_keys"]):
            result["category"] = "engineering"
            result["confidence"] = max(result["confidence"], 0.7)
        elif any(kw in filename_lower for kw in ["readback", "scatter", "dump", "full_backup"]):
            result["category"] = "readback"
            result["confidence"] = max(result["confidence"], 0.7)
        elif any(kw in filename_lower for kw in ["mod", "debloat", "root", "twrp", "magisk", "custom"]):
            result["category"] = "modified"
            result["confidence"] = max(result["confidence"], 0.6)
            # Subtype detection for modified
            for subtype in MODIFIED_SUBTYPES:
                if subtype.replace("_", "") in filename_lower or subtype in filename_lower:
                    result["subtype"] = subtype
                    break

        # Chipset detection
        chipset_patterns = {
            "mediatek": [r"mt\d{4}", r"helio", r"mediatek"],
            "qualcomm": [r"msm\d{4}", r"sdm\d{3}", r"sm\d{4}", r"snapdragon", r"qcom"],
            "exynos": [r"exynos", r"s5e\d{4}"],
            "kirin": [r"kirin", r"hi\d{4}"],
            "unisoc": [r"unisoc", r"sc\d{4}", r"spreadtrum"],
            "apple": [r"a\d{2}[-_]?bionic", r"m\d[-_]?chip"],
        }

        for chipset, patterns in chipset_patterns.items():
            for pattern in patterns:
                if re.search(pattern, filename_lower):
                    result["chipset"] = chipset
                    result["confidence"] = max(result["confidence"], 0.5)
                    break
            if "chipset" in result:
                break

        # Partition detection from filename
        partition_keywords = ["boot", "recovery", "system", "vendor", "super", "preloader", "lk", "logo", "modem", "tz", "sbl", "abl", "dtbo", "vbmeta"]
        found_partitions = [p for p in partition_keywords if p in filename_lower]
        if found_partitions:
            result["partitions"] = found_partitions

        return result

    def _analyze_with_ai(self, filename: str, file_size: int, password: Optional[str] = None) -> Optional[dict]:
        """Use AI for advanced firmware analysis."""
        if not AI_AVAILABLE:
            return None

        # Check cache first
        cache_key = f"firmware_ai_analysis:{hash(filename):x}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Rate limiting
        if self.rate_limiter and not self.rate_limiter.is_allowed():
            logger.warning("Firmware AI analysis rate limited")
            return None

        try:
            config = _load_config()

            system_prompt = """You are a firmware analysis expert. Analyze the filename and determine:
1. Brand (e.g., Samsung, Xiaomi, OPPO)
2. Model (e.g., SM-A525F, Redmi Note 10)
3. Variant (e.g., Global, China, India)
4. Category: one of 'official', 'engineering', 'readback', 'modified', 'other'
5. Subtype (for modified firmware: cn_to_global, debloated, pre_rooted, etc.)
6. Chipset (e.g., MediaTek MT6768, Qualcomm SDM660)

Respond in JSON format only, no other text."""

            user_prompt = f"""Analyze this firmware file:
Filename: {filename}
File size: {file_size} bytes
Password protected: {bool(password)}

Return JSON with: brand, model, variant, category, subtype, chipset"""

            with self.circuit_breaker:
                response = _call_openai_response(config, system_prompt, user_prompt)

                # Parse JSON response
                try:
                    # Extract JSON from response (handle markdown code blocks)
                    json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        # Validate and normalize
                        normalized = {
                            "brand": str(result.get("brand", "")).strip(),
                            "model": str(result.get("model", "")).strip(),
                            "variant": str(result.get("variant", "")).strip(),
                            "category": str(result.get("category", "")).lower() if result.get("category") else None,
                            "subtype": str(result.get("subtype", "")).lower() if result.get("subtype") else None,
                            "chipset": str(result.get("chipset", "")).strip(),
                        }

                        # Validate category
                        if normalized["category"] not in [k for k, _ in MAIN_CATEGORIES]:
                            normalized["category"] = None

                        # Cache successful result
                        cache.set(cache_key, normalized, timeout=86400)  # 24 hours
                        return normalized
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse AI response as JSON: {response[:200]}")

        except AiClientError as e:
            logger.warning(f"AI client error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in firmware AI analysis: {e}")

        return None

    def propose_schema(self, brand_name: str, context: dict | None = None) -> dict:
        """
        Propose a firmware schema for a brand based on AI analysis.
        
        Args:
            brand_name: Name of the brand
            context: Optional context with existing patterns
            
        Returns:
            Dict with schema suggestions
        """
        default_schema = {
            "chipset_patterns": [],
            "naming_patterns": [],
            "engineering_subtypes": [],
            "modified_subtypes": list(MODIFIED_SUBTYPES),
            "other_firmware_subtypes": [],
            "variant_rules": [],
            "region_codes": [],
            "board_id_patterns": [],
            "flash_formats": [],
        }

        if not AI_AVAILABLE or not getattr(settings, 'AI_OPENAI_API_KEY', None):
            # Return heuristic-based schema for known brands
            return self._get_heuristic_schema(brand_name)

        # Check cache
        cache_key = f"firmware_schema:{brand_name.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        try:
            config = _load_config()

            system_prompt = """You are a mobile device firmware expert. Generate a firmware schema for the given brand.
Include: chipset patterns, naming conventions, region codes, flash formats, etc.
Respond in JSON format only."""

            user_prompt = f"""Generate firmware schema for brand: {brand_name}
Context: {json.dumps(context or {})}

Return JSON with: chipset_patterns, naming_patterns, variant_rules, region_codes, board_id_patterns, flash_formats"""

            if self.rate_limiter and not self.rate_limiter.is_allowed():
                return default_schema

            with self.circuit_breaker:
                response = _call_openai_response(config, system_prompt, user_prompt)

                try:
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        merged = {**default_schema, **result}
                        cache.set(cache_key, merged, timeout=604800)  # 7 days
                        return merged
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse schema response: {response[:200]}")

        except Exception as e:
            logger.error(f"Error proposing schema: {e}")

        return self._get_heuristic_schema(brand_name)

    def _get_heuristic_schema(self, brand_name: str) -> dict:
        """Get pre-defined schema patterns for known brands."""
        brand_lower = brand_name.lower()

        schemas = {
            "samsung": {
                "chipset_patterns": ["exynos", "snapdragon", "mediatek"],
                "naming_patterns": ["SM-[A-Z]\\d{3}[A-Z]?"],
                "region_codes": ["XAR", "XSG", "DBT", "BTU", "SER", "INS", "TPA"],
                "flash_formats": ["odin", "tar.md5"],
            },
            "xiaomi": {
                "chipset_patterns": ["snapdragon", "mediatek", "dimensity"],
                "naming_patterns": ["\\d{5}", "\\d{4}[A-Z]{3}"],
                "region_codes": ["CN", "IN", "EU", "RU", "ID"],
                "flash_formats": ["fastboot", "miflash", "tgz"],
            },
            "oppo": {
                "chipset_patterns": ["snapdragon", "mediatek", "dimensity"],
                "naming_patterns": ["CPH\\d{4}", "PDBM\\d{2}"],
                "region_codes": ["IN", "CN", "EU", "MEA"],
                "flash_formats": ["ofp", "scatter"],
            },
        }

        base_schema = {
            "chipset_patterns": [],
            "naming_patterns": [],
            "engineering_subtypes": ["userdebug", "eng", "test_keys"],
            "modified_subtypes": list(MODIFIED_SUBTYPES),
            "other_firmware_subtypes": ["dump", "backup", "tool"],
            "variant_rules": [],
            "region_codes": [],
            "board_id_patterns": [],
            "flash_formats": [],
        }

        return {**base_schema, **schemas.get(brand_lower, {})}
