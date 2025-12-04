
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def aggregate_events() -> None:
    """
    Aggregate ad events in the background.

    In the default configuration this is a no-op that can be safely scheduled;
    worker-backed deployments may override or wrap this for real aggregation.
    """
    logger.info("ads.tasks.aggregate_events invoked")


