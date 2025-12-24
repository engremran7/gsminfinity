from __future__ import annotations

import random
from typing import Optional
from django.utils import timezone
from django.db.models import F, Q, Sum
from django.core.cache import cache
from ..models import SharedDriveAccount, ServiceAccount
import logging

logger = logging.getLogger(__name__)


class ServiceAccountRouter:
    """
    Intelligently selects service accounts to maximize throughput
    while respecting 750GB/day quota per account
    """
    
    def __init__(self):
        self.cache_timeout = 60  # Cache SA selection for 1 minute
    
    def get_best_service_account(
        self, 
        required_gb: float = 1.0, 
        exclude_ids: list = None,
        preferred_drive_id: str = None
    ) -> Optional[ServiceAccount]:
        """
        Select optimal service account based on:
        1. Available quota (750GB/day)
        2. Performance (average speed)
        3. Health status (consecutive failures)
        4. Load balancing (last_used_at)
        5. Preferred shared drive (if specified)
        
        Args:
            required_gb: Size of transfer in GB
            exclude_ids: List of SA IDs to exclude
            preferred_drive_id: Preferred shared drive UUID
            
        Returns:
            ServiceAccount or None if no suitable account found
        """
        exclude_ids = exclude_ids or []
        
        # Check cache first
        cache_key = f'best_sa_{required_gb}_{hash(tuple(exclude_ids))}_{preferred_drive_id}'
        cached = cache.get(cache_key)
        if cached:
            sa = ServiceAccount.objects.filter(id=cached).first()
            if sa and sa.available_quota_gb() >= required_gb:
                return sa
        
        # Build query
        now = timezone.now()
        candidates = ServiceAccount.objects.filter(
            is_active=True,
            is_banned=False,
            consecutive_failures__lt=3,
            shared_drive__is_active=True
        ).exclude(
            id__in=exclude_ids
        ).select_related('shared_drive')
        
        # Filter by preferred drive if specified
        if preferred_drive_id:
            candidates = candidates.filter(shared_drive__id=preferred_drive_id)
        
        # Filter by available quota
        candidates = [sa for sa in candidates if sa.available_quota_gb() >= required_gb]
        
        if not candidates:
            # Try to reset expired quotas and retry
            self._reset_expired_quotas()
            logger.warning(f"No service accounts with {required_gb}GB available quota")
            return None
        
        # Score each candidate
        scored = []
        for sa in candidates:
            score = self._calculate_score(sa, required_gb)
            scored.append((score, sa))
        
        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Pick top 3 and randomize to distribute load
        top_count = min(3, len(scored))
        top_candidates = scored[:top_count]
        _, selected = random.choice(top_candidates)
        
        # Cache selection
        cache.set(cache_key, selected.id, self.cache_timeout)
        
        logger.info(f"Selected SA: {selected.name} with {selected.available_quota_gb():.1f}GB available")
        return selected
    
    def _calculate_score(self, sa: ServiceAccount, required_gb: float) -> float:
        """
        Scoring algorithm:
        - 40% weight: Available quota ratio
        - 30% weight: Performance (speed)
        - 20% weight: Freshness (least recently used)
        - 10% weight: Reliability (low failure rate)
        """
        now = timezone.now()
        
        # Quota score (0-100)
        available = sa.available_quota_gb()
        quota_ratio = available / sa.daily_quota_gb if sa.daily_quota_gb > 0 else 0
        quota_score = quota_ratio * 100
        
        # Performance score (0-100)
        max_speed = 100  # Assume 100 Mbps as max
        speed_score = min((sa.average_speed_mbps / max_speed) * 100, 100) if max_speed > 0 else 50
        
        # Freshness score (0-100)
        if sa.last_used_at:
            minutes_since_use = (now - sa.last_used_at).total_seconds() / 60
            freshness_score = min(minutes_since_use / 10, 100)  # 10 min = 100 points
        else:
            freshness_score = 100  # Never used = fresh
        
        # Reliability score (0-100)
        reliability_score = max(100 - (sa.consecutive_failures * 50), 0)
        
        # Weighted total
        total_score = (
            quota_score * 0.4 +
            speed_score * 0.3 +
            freshness_score * 0.2 +
            reliability_score * 0.1
        )
        
        return total_score
    
    def _reset_expired_quotas(self):
        """Reset quotas for accounts past midnight"""
        now = timezone.now()
        expired = ServiceAccount.objects.filter(quota_reset_at__lt=now)
        
        count = 0
        for sa in expired:
            sa.used_quota_today_gb = 0.0
            sa.quota_reset_at = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timezone.timedelta(days=1)
            sa.save(update_fields=['used_quota_today_gb', 'quota_reset_at'])
            count += 1
        
        if count > 0:
            logger.info(f"Reset quota for {count} service accounts")
    
    def get_shared_drive_distribution(self) -> list[dict]:
        """Get current load distribution across all shared drives"""
        drives = SharedDriveAccount.objects.filter(is_active=True)
        
        distribution = []
        for drive in drives:
            sas = drive.service_accounts.filter(is_active=True)
            
            total_quota = sas.aggregate(total=Sum('daily_quota_gb'))['total'] or 0
            used_quota = sas.aggregate(used=Sum('used_quota_today_gb'))['used'] or 0
            
            distribution.append({
                'drive_id': str(drive.id),
                'drive_name': drive.name,
                'total_quota_gb': total_quota,
                'used_quota_gb': used_quota,
                'available_quota_gb': total_quota - used_quota,
                'utilization_percent': (used_quota / total_quota * 100) if total_quota > 0 else 0,
                'active_accounts': sas.count(),
                'file_count': drive.current_file_count,
                'max_files': drive.max_files,
                'file_utilization_percent': drive.utilization_percent(),
                'health_status': drive.health_status
            })
        
        return distribution
    
    def predict_exhaustion_time(self, current_rate_gb_per_hour: float) -> Optional[timezone.datetime]:
        """Predict when all service accounts will be exhausted"""
        total_available = 0
        
        for sa in ServiceAccount.objects.filter(is_active=True, is_banned=False):
            total_available += sa.available_quota_gb()
        
        if current_rate_gb_per_hour == 0 or total_available == 0:
            return None
        
        hours_remaining = total_available / current_rate_gb_per_hour
        exhaustion_time = timezone.now() + timezone.timedelta(hours=hours_remaining)
        
        return exhaustion_time
    
    def rotate_on_failure(
        self, 
        failed_sa_id: str, 
        required_gb: float,
        preferred_drive_id: str = None
    ) -> Optional[ServiceAccount]:
        """Get alternative SA when one fails"""
        try:
            failed_sa = ServiceAccount.objects.get(id=failed_sa_id)
            failed_sa.consecutive_failures += 1
            failed_sa.save(update_fields=['consecutive_failures'])
            
            # If 3 consecutive failures, disable temporarily
            if failed_sa.consecutive_failures >= 3:
                failed_sa.is_active = False
                failed_sa.save(update_fields=['is_active'])
                logger.error(f"Service account {failed_sa.name} disabled after 3 failures")
        except ServiceAccount.DoesNotExist:
            logger.error(f"Failed SA {failed_sa_id} not found")
        
        # Get alternative
        return self.get_best_service_account(
            required_gb=required_gb,
            exclude_ids=[failed_sa_id],
            preferred_drive_id=preferred_drive_id
        )
    
    def record_successful_operation(
        self, 
        sa_id: str, 
        bytes_transferred: int,
        speed_mbps: float = None
    ):
        """
        Record successful operation with atomic updates to prevent race conditions
        Critical for high-concurrency scenarios
        """
        try:
            from django.db import transaction
            
            with transaction.atomic():
                # Lock row for update to prevent race conditions on quota counting
                sa = ServiceAccount.objects.select_for_update().get(id=sa_id)
                
                gb_transferred = bytes_transferred / (1024 ** 3)
                
                # Use F() expressions for atomic increments (thread-safe)
                ServiceAccount.objects.filter(id=sa_id).update(
                    used_quota_today_gb=F('used_quota_today_gb') + gb_transferred,
                    total_bytes_transferred=F('total_bytes_transferred') + bytes_transferred,
                    total_operations=F('total_operations') + 1,
                    consecutive_failures=0,  # Reset on success
                    last_used_at=timezone.now()
                )
                
                # Speed update requires read-modify-write (can't use F() with calculations)
                if speed_mbps:
                    sa.refresh_from_db()
                    if sa.average_speed_mbps == 0:
                        sa.average_speed_mbps = speed_mbps
                    else:
                        # Exponential moving average: 80% old, 20% new
                        sa.average_speed_mbps = (sa.average_speed_mbps * 0.8) + (speed_mbps * 0.2)
                    sa.save(update_fields=['average_speed_mbps'])
                
                logger.info(f"Recorded {gb_transferred:.2f}GB transfer for SA {sa.name} (atomic)")
            
        except ServiceAccount.DoesNotExist:
            logger.error(f"Service account {sa_id} not found for operation recording")
        except Exception as e:
            logger.error(f"Failed to record operation for SA {sa_id}: {e}")
