
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def aggregate_events():
    """
    Placeholder Celery task to aggregate ad events; wire Celery/RQ in production.
    """
    logger.info("ads.tasks.aggregate_events noop placeholder")


