
from __future__ import annotations

from . import LoggingConnector


class GoogleIndexingConnector(LoggingConnector):
    channel = "google_indexing"


class BingConnector(LoggingConnector):
    channel = "bing_indexing"


