
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_sitemap_async():
    logger.info("seo.tasks.build_sitemap_async noop placeholder")


def check_links_async():
    logger.info("seo.tasks.check_links_async noop placeholder")


def inspect_url_async(url: str):
    logger.info("seo.tasks.inspect_url_async noop placeholder for %s", url)


