
from __future__ import annotations

from . import StubConnector


class GoogleIndexingConnector(StubConnector):
    channel = "google_indexing"


class BingConnector(StubConnector):
    channel = "bing_indexing"


