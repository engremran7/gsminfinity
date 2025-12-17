from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional, Set, cast
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta

from apps.ads.models_enhanced import (
    Campaign, AdPlacement, AdCreative, AdAnalytics
)
from apps.core.ai_client import (
    generate_personalized_ad_content,
    predict_campaign_performance,
)

logger = logging.getLogger(__name__)


class AdvancedTargetingEngine:
    """
    Enterprise-grade targeting engine with AI-powered audience segmentation,
    real-time bidding, and advanced contextual targeting.
    """

    def __init__(self, tenant_id: str = ""):
        self.tenant_id = tenant_id
        self.cache_timeout = 1800  # 30 minutes

    def evaluate_campaign_eligibility(self, campaign: Campaign,
                                    context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive campaign eligibility evaluation with advanced targeting.
        """
        reasons = []
        score = 0
        max_score = 100

        # Basic checks
        if not campaign.is_live():
            reasons.append("Campaign not active")
            return {"eligible": False, "reasons": reasons, "score": 0}

        # Budget checks
        if not self._check_budget_limits(campaign):
            reasons.append("Budget limits exceeded")
            return {"eligible": False, "reasons": reasons, "score": 0}

        # Advanced targeting evaluation
        targeting_score = self._evaluate_targeting_rules(campaign, context)
        score += targeting_score

        # Contextual relevance
        context_score = self._evaluate_contextual_relevance(campaign, context)
        score += context_score

        # Behavioral targeting
        behavior_score = self._evaluate_behavioral_targeting(campaign, context)
        score += behavior_score

        # Predictive scoring
        predictive_score = self._calculate_predictive_score(campaign, context)
        score += predictive_score

        # Frequency capping
        if self._check_frequency_capping(campaign, context):
            reasons.append("Frequency cap exceeded")
            return {"eligible": False, "reasons": reasons, "score": 0}

        eligible = score >= 40  # Minimum threshold

        return {
            "eligible": eligible,
            "score": min(score, max_score),
            "reasons": reasons,
            "targeting_breakdown": {
                "basic_targeting": targeting_score,
                "contextual": context_score,
                "behavioral": behavior_score,
                "predictive": predictive_score
            }
        }

    def select_optimal_creative(self, campaign: Campaign, placement: AdPlacement,
                               context: Dict[str, Any]) -> Optional[AdCreative]:
        """
        Select optimal creative using advanced algorithms.
        """
        # Get eligible creatives
        eligible_creatives = self._get_eligible_creatives(campaign, placement, context)

        if not eligible_creatives:
            return None

        # Score creatives based on multiple factors
        scored_creatives = []
        for creative in eligible_creatives:
            score = self._score_creative_for_context(creative, placement, context)
            scored_creatives.append((creative, score))

        # Sort by score and apply randomization for exploration
        scored_creatives.sort(key=lambda x: x[1], reverse=True)

        # Thompson sampling for exploration vs exploitation
        selected_creative = self._apply_exploration_strategy(scored_creatives)

        return selected_creative

    def calculate_real_time_bid(self, campaign: Campaign, placement: AdPlacement,
                               context: Dict[str, Any]) -> float:
        """
        Calculate real-time bid using predictive modeling.
        """
        base_bid = campaign.get_current_bid()

        # Market conditions adjustment
        market_multiplier = self._get_market_conditions_multiplier(context)

        # Inventory scarcity adjustment
        scarcity_multiplier = self._calculate_inventory_scarity(placement, context)

        # Audience value adjustment
        audience_multiplier = self._calculate_audience_value(context)

        # Predictive adjustment
        predictive_multiplier = self._get_predictive_bid_adjustment(campaign, context)

        final_bid = base_bid * market_multiplier * scarcity_multiplier * audience_multiplier * predictive_multiplier

        # Apply bid constraints
        final_bid = max(final_bid, campaign.target_cpa * 0.1)  # Minimum bid
        final_bid = min(final_bid, campaign.max_bid)  # Maximum bid

        return round(final_bid, 2)

    def get_personalized_content(self, creative: AdCreative, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate personalized content for dynamic creatives.
        """
        if not creative.dynamic_enabled:
            return {"html": creative.html, "personalized": False}

        try:
            # AI-powered personalization
            personalized_content = generate_personalized_ad_content({
                "creative_id": creative.id,
                "user_context": context,
                "creative_template": creative.html,
                "dynamic_variables": creative.dynamic_variables
            })

            return {
                "html": personalized_content.get("html", creative.html),
                "personalized": True,
                "confidence": personalized_content.get("confidence", 0.5)
            }
        except Exception as e:
            logger.error(f"Personalization failed: {e}")
            return {"html": creative.html, "personalized": False}

    def _evaluate_targeting_rules(self, campaign: Campaign, context: Dict[str, Any]) -> int:
        """Evaluate campaign targeting rules."""
        score = 0

        # Geographic targeting
        if campaign.targeting_rules.get("geo_enabled"):
            user_country = context.get("country", "").upper()
            target_countries = campaign.targeting_rules.get("countries", [])
            if target_countries and user_country in [c.upper() for c in target_countries]:
                score += 20
            elif not target_countries:  # No restrictions
                score += 10

        # Device targeting
        device_type = context.get("device_type", "").lower()
        target_devices = campaign.targeting_rules.get("devices", [])
        if target_devices and device_type in [d.lower() for d in target_devices]:
            score += 15
        elif not target_devices:
            score += 10

        # Time targeting
        if self._check_time_targeting(campaign, context):
            score += 15

        # Audience segment targeting
        if self._check_audience_segments(campaign, context):
            score += 20

        return min(score, 40)

    def _evaluate_contextual_relevance(self, campaign: Campaign, context: Dict[str, Any]) -> int:
        """Evaluate contextual relevance."""
        score = 0

        page_context = context.get("page_context", "")
        content_tags = set(context.get("content_tags", []))

        # Page context matching
        if page_context in campaign.targeting_rules.get("page_contexts", []):
            score += 15

        # Content tag matching
        target_tags = set(campaign.targeting_rules.get("content_tags", []))
        if target_tags and content_tags:
            overlap = len(target_tags & content_tags)
            if overlap > 0:
                score += min(overlap * 5, 15)

        # Keyword matching
        keywords = campaign.targeting_rules.get("keywords", [])
        page_keywords = context.get("page_keywords", [])
        if keywords and page_keywords:
            keyword_matches = len(set(keywords) & set(page_keywords))
            if keyword_matches > 0:
                score += min(keyword_matches * 3, 10)

        return min(score, 25)

    def _evaluate_behavioral_targeting(self, campaign: Campaign, context: Dict[str, Any]) -> int:
        """Evaluate behavioral targeting."""
        score = 0

        user_id = context.get("user_id")
        if not user_id:
            return 0

        # Check user behavior history
        behavior_score = self._analyze_user_behavior(user_id, campaign)
        score += min(behavior_score, 20)

        # Check retargeting eligibility
        if self._check_retargeting_eligibility(user_id, campaign):
            score += 10

        return min(score, 25)

    def _calculate_predictive_score(self, campaign: Campaign, context: Dict[str, Any]) -> int:
        """Calculate predictive performance score."""
        try:
            features = self._extract_prediction_features(campaign, context)
            prediction = predict_campaign_performance(features)
            confidence = prediction.get("confidence", 0.5)
            return int(confidence * 10)
        except Exception:
            return 5  # Default moderate score

    def _check_budget_limits(self, campaign: Campaign) -> bool:
        """Check if campaign is within budget limits."""
        # This would integrate with real-time budget tracking
        # For now, return True
        return True

    def _check_frequency_capping(self, campaign: Campaign, context: Dict[str, Any]) -> bool:
        """Check frequency capping rules."""
        user_id = context.get("user_id")
        if not user_id:
            return False

        # Check recent impressions for this user
        recent_impressions = AdAnalytics.objects.filter(
            user_id=user_id,
            campaign=campaign,
            event_type="impression",
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).count()

        return recent_impressions >= 3  # Example cap

    def _get_eligible_creatives(self, campaign: Campaign, placement: AdPlacement,
                               context: Dict[str, Any]) -> List[AdCreative]:
        """Get creatives eligible for the placement and context."""
        creatives = AdCreative.objects.filter(
            campaign=campaign,
            is_active=True,
            is_enabled=True,
            tenant_id=self.tenant_id
        )

        eligible = []
        for creative in creatives:
            if self._is_creative_eligible(creative, placement, context):
                eligible.append(creative)

        return eligible

    def _is_creative_eligible(self, creative: AdCreative, placement: AdPlacement,
                            context: Dict[str, Any]) -> bool:
        """Check if creative is eligible for placement and context."""
        # Size compatibility
        if placement.allowed_sizes and creative.size_category not in placement.allowed_sizes:
            return False

        # Type compatibility
        if placement.allowed_types and creative.creative_type not in placement.allowed_types:
            return False

        # Mobile compatibility
        if context.get("device_type") == "mobile" and not creative.mobile_optimized:
            return False

        return True

    def _score_creative_for_context(self, creative: AdCreative, placement: AdPlacement,
                                  context: Dict[str, Any]) -> float:
        """Score creative relevance for the given context."""
        score = creative.performance_score

        # Contextual relevance bonus
        if context.get("device_type") == "mobile" and creative.mobile_optimized:
            score += 2

        # A/B testing adjustment
        if creative.ab_test_group:
            score += 1

        # Performance history bonus
        recent_performance = self._get_recent_creative_performance(creative, placement)
        score += recent_performance * 0.1

        return score

    def _apply_exploration_strategy(self, scored_creatives: List[tuple]) -> Optional[AdCreative]:
        """Apply exploration strategy to creative selection."""
        if not scored_creatives:
            return None

        # 10% exploration, 90% exploitation
        import random
        if random.random() < 0.1:
            # Random selection for exploration
            return random.choice(scored_creatives)[0]
        else:
            # Best performing for exploitation
            return scored_creatives[0][0]

    def _get_market_conditions_multiplier(self, context: Dict[str, Any]) -> float:
        """Calculate market conditions multiplier."""
        # This would analyze current market competition
        return 1.0

    def _calculate_inventory_scarity(self, placement: AdPlacement, context: Dict[str, Any]) -> float:
        """Calculate inventory scarcity multiplier."""
        # Higher multiplier when inventory is scarce
        return 1.0

    def _calculate_audience_value(self, context: Dict[str, Any]) -> float:
        """Calculate audience value multiplier."""
        # Higher for more valuable audiences
        return 1.0

    def _get_predictive_bid_adjustment(self, campaign: Campaign, context: Dict[str, Any]) -> float:
        """Get predictive bid adjustment."""
        return 1.0

    def _check_time_targeting(self, campaign: Campaign, context: Dict[str, Any]) -> bool:
        """Check time-based targeting."""
        if not campaign.dayparting_enabled:
            return True

        current_hour = context.get("hour", datetime.now().hour)
        day_of_week = context.get("day_of_week", datetime.now().weekday())

        schedule = campaign.dayparting_schedule.get(str(day_of_week), [])
        return current_hour in schedule

    def _check_audience_segments(self, campaign: Campaign, context: Dict[str, Any]) -> bool:
        """Check audience segment targeting."""
        user_segments = set(context.get("user_segments", []))
        target_segments = set(campaign.audience_segments)

        if not target_segments:
            return True

        return bool(user_segments & target_segments)

    def _analyze_user_behavior(self, user_id: str, campaign: Campaign) -> int:
        """Analyze user behavior for targeting."""
        # This would analyze user behavior history
        return 10  # Placeholder

    def _check_retargeting_eligibility(self, user_id: str, campaign: Campaign) -> bool:
        """Check if user is eligible for retargeting."""
        # Check if user has interacted with campaign before
        return False  # Placeholder

    def _extract_prediction_features(self, campaign: Campaign, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for performance prediction."""
        return {
            "campaign_type": campaign.type,
            "campaign_age_days": (timezone.now() - campaign.created_at).days,
            "budget": float(campaign.budget),
            "device_type": context.get("device_type", ""),
            "country": context.get("country", ""),
            "hour": context.get("hour", 12),
        }

    def _get_recent_creative_performance(self, creative: AdCreative, placement: AdPlacement) -> float:
        """Get recent performance score for creative."""
        # Cache key for performance data
        cache_key = f"creative_perf_{creative.id}_{placement.id}"
        cached_score = cache.get(cache_key)

        if cached_score is not None:
            return cached_score

        # Calculate recent performance
        seven_days_ago = timezone.now() - timedelta(days=7)
        performance = AdAnalytics.objects.filter(
            creative=creative,
            placement=placement,
            created_at__gte=seven_days_ago
        ).aggregate(
            impressions=Count('id', filter=Q(event_type='impression')),
            clicks=Count('id', filter=Q(event_type='click'))
        )

        impressions = performance['impressions'] or 0
        clicks = performance['clicks'] or 0

        if impressions > 0:
            ctr = (clicks / impressions) * 100
            cache.set(cache_key, ctr, self.cache_timeout)
            return ctr

        # Default when no impressions
        cache.set(cache_key, 0.0, self.cache_timeout)
        return 0.0

    def analyze_targeting_effectiveness(self, campaign: Campaign, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Public wrapper that returns targeting effectiveness summary for a campaign."""
        context = context or {}
        summary = self.evaluate_campaign_eligibility(campaign, context)
        return {
            "eligible": summary.get("eligible", False),
            "score": summary.get("score", 0),
            "breakdown": summary.get("targeting_breakdown", {}),
            "reasons": summary.get("reasons", []),
        }

    def optimize_targeting(self, campaign: Campaign) -> Dict[str, Any]:
        """Perform simple targeting optimization and return recommendations."""
        # For now, return heuristic recommendations based on targeting rules
        recs = []
        rules = getattr(campaign, "targeting_rules", {}) or {}
        if not rules.get("geo_enabled"):
            recs.append({"action": "enable_geo_targeting", "reason": "Geo targeting recommended for better relevance"})
        if not rules.get("devices"):
            recs.append({"action": "add_device_targets", "reason": "Specify devices to improve bidding efficiency"})

        return {"success": True, "recommendations": recs}

    def get_targeting_recommendations(self, placement: AdPlacement, user_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Return targeting recommendations for a placement and optional user context."""
        user_context = user_context or {}
        campaign = getattr(placement, "campaign", None)
        if campaign is None:
            return {"eligible": False, "recommendations": []}

        summary = self.evaluate_campaign_eligibility(campaign, user_context)
        recommendations: List[Dict[str, Any]] = []
        if not summary.get("eligible"):
            recommendations.append({"action": "adjust_targeting", "reason": "Campaign not eligible for this user/context"})

        # Suggest bid multiplier based on score
        score = summary.get("score", 0)
        if score < 50:
            recommendations.append({"action": "increase_bid_multiplier", "value": 1.1, "reason": "Low targeting score"})

        return cast(Dict[str, Any], {"eligible": summary.get("eligible", False), "score": score, "recommendations": recommendations})