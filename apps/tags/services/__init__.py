"""Service layer initialization"""
from apps.tags.services.tagging_service import TaggingService
from apps.tags.services.tag_service import TagService

__all__ = ['TaggingService', 'TagService']
