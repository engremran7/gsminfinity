from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.cache import cache
from datetime import datetime, timedelta

from apps.ads.models_enhanced import (
    Campaign, AdCreative, AdPlacement, AdAnalytics,
    AdPerformanceReport,
    # ABLandingPage  # Commented out - model not yet defined
)
from apps.ads.services.ai_optimizer_enhanced import EnhancedAIOptimizer
from apps.ads.services.targeting_engine_enhanced import AdvancedTargetingEngine
from apps.ads.services.analytics_enhanced import EnhancedAnalyticsService
from apps.ads.services.rotation_enhanced import EnhancedRotationService

logger = logging.getLogger(__name__)


class EnhancedAdsAPIService:
    """
    Enterprise-grade API service integrating all enhanced ad services.
    """

    def __init__(self, tenant_id: str = ""):
        self.tenant_id = tenant_id
        self.ai_optimizer = EnhancedAIOptimizer(tenant_id)
        self.targeting_engine = AdvancedTargetingEngine(tenant_id)
        self.analytics_service = EnhancedAnalyticsService(tenant_id)
        self.rotation_service = EnhancedRotationService(tenant_id)

    def get_campaign_performance(self, campaign_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive campaign performance data.
        """
        try:
            campaign = Campaign.objects.get(id=campaign_id, tenant_id=self.tenant_id)

            # Real-time metrics
            rt_metrics = self.analytics_service.get_real_time_metrics(campaign=campaign, hours=24)

            # Revenue analytics
            revenue_data = self.analytics_service.get_revenue_analytics(campaign=campaign, days=days)

            # Audience insights
            audience_data = self.analytics_service.get_audience_insights(campaign, days)

            # AI insights
            ai_insights = self.ai_optimizer.generate_campaign_insights(campaign)

            # Targeting effectiveness
            targeting_effectiveness = self.targeting_engine.analyze_targeting_effectiveness(campaign)

            return {
                "campaign_id": campaign_id,
                "campaign_name": campaign.name,
                "status": "success",
                "data": {
                    "real_time_metrics": rt_metrics,
                    "revenue_analytics": revenue_data,
                    "audience_insights": audience_data,
                    "ai_insights": ai_insights,
                    "targeting_effectiveness": targeting_effectiveness,
                    "performance_score": campaign.performance_score,
                    "optimization_recommendations": campaign.get_optimization_recommendations()
                }
            }

        except Campaign.DoesNotExist:
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": "Campaign not found"
            }
        except Exception as e:
            logger.error(f"Error getting campaign performance: {e}")
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": str(e)
            }

    def optimize_campaign(self, campaign_id: int, optimization_type: str = "auto") -> Dict[str, Any]:
        """
        Optimize campaign using AI and analytics.
        """
        try:
            campaign = Campaign.objects.get(id=campaign_id, tenant_id=self.tenant_id)

            if optimization_type == "auto":
                # Full AI optimization
                optimization_result = self.ai_optimizer.optimize_campaign(campaign)
            elif optimization_type == "budget":
                # Budget optimization
                optimization_result = self.ai_optimizer.optimize_budget_allocation(campaign)
            elif optimization_type == "targeting":
                # Targeting optimization
                optimization_result = self.targeting_engine.optimize_targeting(campaign)
            elif optimization_type == "creative":
                # Creative optimization
                optimization_result = self.ai_optimizer.optimize_creative_performance(campaign)
            else:
                return {
                    "campaign_id": campaign_id,
                    "status": "error",
                    "error": f"Unknown optimization type: {optimization_type}"
                }

            # Apply optimizations if successful
            if optimization_result.get("success"):
                self._apply_optimization_changes(campaign, optimization_result)

            return {
                "campaign_id": campaign_id,
                "status": "success",
                "optimization_type": optimization_type,
                "result": optimization_result
            }

        except Campaign.DoesNotExist:
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": "Campaign not found"
            }
        except Exception as e:
            logger.error(f"Error optimizing campaign: {e}")
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": str(e)
            }

    def get_ad_recommendations(self, placement_id: int, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get AI-powered ad recommendations for a placement.
        """
        try:
            placement = AdPlacement.objects.get(id=placement_id, tenant_id=self.tenant_id)

            # Get targeting recommendations
            targeting_recs = self.targeting_engine.get_targeting_recommendations(placement, user_context)

            # Get creative recommendations
            creative_recs = self.ai_optimizer.get_creative_recommendations(placement)

            # Get rotation optimization
            rotation_opt = self.rotation_service.optimize_rotation_settings(placement)

            return {
                "placement_id": placement_id,
                "status": "success",
                "recommendations": {
                    "targeting": targeting_recs,
                    "creative": creative_recs,
                    "rotation": rotation_opt
                }
            }

        except AdPlacement.DoesNotExist:
            return {
                "placement_id": placement_id,
                "status": "error",
                "error": "Placement not found"
            }
        except Exception as e:
            logger.error(f"Error getting ad recommendations: {e}")
            return {
                "placement_id": placement_id,
                "status": "error",
                "error": str(e)
            }

    def run_ab_test(self, campaign_id: int, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run A/B test for campaign optimization.
        """
        try:
            campaign = Campaign.objects.get(id=campaign_id, tenant_id=self.tenant_id)

            # Validate test configuration
            validation_result = self._validate_ab_test_config(test_config)
            if not validation_result["valid"]:
                return {
                    "campaign_id": campaign_id,
                    "status": "error",
                    "error": validation_result["error"]
                }

            # Create A/B test
            test_result = self.ai_optimizer.create_ab_test(campaign, test_config)

            return {
                "campaign_id": campaign_id,
                "status": "success",
                "test_id": test_result.get("test_id"),
                "test_config": test_config,
                "result": test_result
            }

        except Campaign.DoesNotExist:
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": "Campaign not found"
            }
        except Exception as e:
            logger.error(f"Error running A/B test: {e}")
            return {
                "campaign_id": campaign_id,
                "status": "error",
                "error": str(e)
            }

    def get_analytics_dashboard(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get comprehensive analytics dashboard data.
        """
        try:
            filters = filters or {}

            # Date range
            days = filters.get("days", 30)
            start_date = timezone.now() - timedelta(days=days)

            # Base filters
            query_filters = Q(created_at__gte=start_date, tenant_id=self.tenant_id)

            if filters.get("campaign_id"):
                query_filters &= Q(campaign_id=filters["campaign_id"])
            if filters.get("creative_id"):
                query_filters &= Q(creative_id=filters["creative_id"])
            if filters.get("placement_id"):
                query_filters &= Q(placement_id=filters["placement_id"])

            # Aggregate metrics
            dashboard_data = AdAnalytics.objects.filter(query_filters).aggregate(
                total_impressions=Count('id', filter=Q(event_type='impression')),
                total_clicks=Count('id', filter=Q(event_type='click')),
                total_conversions=Count('id', filter=Q(event_type='conversion')),
                total_revenue=Sum('event_value', filter=Q(event_type='conversion')),
                total_cost=Sum('event_value', filter=Q(event_type='cost')),
                total_views=Count('id', filter=Q(event_type='view')),
                total_engagements=Count('id', filter=Q(event_type='engagement'))
            )

            # Calculate derived metrics
            impressions = dashboard_data['total_impressions'] or 0
            clicks = dashboard_data['total_clicks'] or 0
            conversions = dashboard_data['total_conversions'] or 0
            revenue = dashboard_data['total_revenue'] or 0
            cost = dashboard_data['total_cost'] or 0

            derived_metrics = {
                "ctr": (clicks / impressions * 100) if impressions > 0 else 0,
                "cpc": cost / clicks if clicks > 0 else 0,
                "cpm": (cost / impressions * 1000) if impressions > 0 else 0,
                "cpa": cost / conversions if conversions > 0 else 0,
                "conversion_rate": (conversions / clicks * 100) if clicks > 0 else 0,
                "roi": ((revenue - cost) / cost * 100) if cost > 0 else 0,
                "roas": revenue / cost if cost > 0 else 0
            }

            # Top performing campaigns
            top_campaigns = AdAnalytics.objects.filter(query_filters).values(
                'campaign__name'
            ).annotate(
                impressions=Count('id', filter=Q(event_type='impression')),
                clicks=Count('id', filter=Q(event_type='click')),
                conversions=Count('id', filter=Q(event_type='conversion')),
                revenue=Sum('event_value', filter=Q(event_type='conversion'))
            ).order_by('-revenue')[:10]

            # Geographic breakdown
            geo_breakdown = AdAnalytics.objects.filter(query_filters).values(
                'country'
            ).annotate(
                impressions=Count('id', filter=Q(event_type='impression')),
                clicks=Count('id', filter=Q(event_type='click'))
            ).order_by('-impressions')[:10]

            # Device breakdown
            device_breakdown = AdAnalytics.objects.filter(query_filters).values(
                'device_type'
            ).annotate(
                impressions=Count('id', filter=Q(event_type='impression')),
                clicks=Count('id', filter=Q(event_type='click'))
            ).order_by('-impressions')

            return {
                "status": "success",
                "period_days": days,
                "summary_metrics": dashboard_data,
                "derived_metrics": derived_metrics,
                "top_campaigns": list(top_campaigns),
                "geographic_breakdown": list(geo_breakdown),
                "device_breakdown": list(device_breakdown),
                "filters_applied": filters
            }

        except Exception as e:
            logger.error(f"Error getting analytics dashboard: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def generate_report(self, report_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate custom performance report.
        """
        try:
            report_type = report_config.get("type", "campaign_performance")
            report_date = report_config.get("date", timezone.now().date())
            period = report_config.get("period", "daily")

            # Generate report
            report = self.analytics_service.generate_performance_report(
                report_type, report_date, period, **report_config.get("filters", {})
            )

            return {
                "status": "success",
                "report_id": report.id,
                "report_type": report_type,
                "report_date": report_date,
                "period": period,
                "data": {
                    "impressions": report.impressions,
                    "clicks": report.clicks,
                    "conversions": report.conversions,
                    "revenue": report.revenue,
                    "cost": report.cost,
                    "ctr": report.ctr,
                    "cpc": report.cpc,
                    "cpa": report.cpa,
                    "roi": report.roi,
                    "top_countries": report.top_countries,
                    "device_breakdown": report.device_breakdown
                }
            }

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _validate_ab_test_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate A/B test configuration.
        """
        required_fields = ["name", "variants", "test_duration_days", "traffic_split"]
        for field in required_fields:
            if field not in config:
                return {"valid": False, "error": f"Missing required field: {field}"}

        variants = config.get("variants", [])
        if len(variants) < 2:
            return {"valid": False, "error": "A/B test must have at least 2 variants"}

        traffic_split = config.get("traffic_split", [])
        if len(traffic_split) != len(variants):
            return {"valid": False, "error": "Traffic split must match number of variants"}

        if sum(traffic_split) != 100:
            return {"valid": False, "error": "Traffic split must total 100%"}

        return {"valid": True}

    def _apply_optimization_changes(self, campaign: Campaign, optimization_result: Dict[str, Any]):
        """
        Apply optimization changes to campaign.
        """
        changes = optimization_result.get("changes", {})

        # Update campaign settings
        for key, value in changes.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)

        # Update creative weights
        creative_changes = changes.get("creative_weights", {})
        for creative_id, weight in creative_changes.items():
            try:
                creative = AdCreative.objects.get(id=creative_id, campaign=campaign)
                creative.rotation_weight = weight
                creative.save()
            except AdCreative.DoesNotExist:
                continue

        # Update targeting settings
        targeting_changes = changes.get("targeting", {})
        for key, value in targeting_changes.items():
            if hasattr(campaign, f"target_{key}"):
                setattr(campaign, f"target_{key}", value)

        campaign.save()


# API ViewSet for enhanced ads management
class EnhancedAdsAPIViewSet(ModelViewSet):
    """
    Enhanced API viewset for ads management with AI and analytics.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_service = EnhancedAdsAPIService()

    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Get campaign performance data."""
        days = int(request.query_params.get('days', 30))
        result = self.api_service.get_campaign_performance(int(pk), days)
        return Response(result)

    @action(detail=True, methods=['post'])
    def optimize(self, request, pk=None):
        """Optimize campaign performance."""
        optimization_type = request.data.get('optimization_type', 'auto')
        result = self.api_service.optimize_campaign(int(pk), optimization_type)
        return Response(result)

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Get ad recommendations for placement."""
        placement_id = request.query_params.get('placement_id')
        user_context = request.query_params.get('user_context', {})

        if not placement_id:
            return Response({"error": "placement_id required"}, status=status.HTTP_400_BAD_REQUEST)

        result = self.api_service.get_ad_recommendations(int(placement_id), user_context)
        return Response(result)

    @action(detail=True, methods=['post'])
    def ab_test(self, request, pk=None):
        """Run A/B test for campaign."""
        test_config = request.data
        result = self.api_service.run_ab_test(int(pk), test_config)
        return Response(result)

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get analytics dashboard."""
        filters = request.query_params.dict()
        result = self.api_service.get_analytics_dashboard(filters)
        return Response(result)

    @action(detail=False, methods=['post'])
    def generate_report(self, request):
        """Generate custom report."""
        report_config = request.data
        result = self.api_service.generate_report(report_config)
        return Response(result)