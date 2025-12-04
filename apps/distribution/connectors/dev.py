
from __future__ import annotations

from . import StubConnector


class DevtoConnector(StubConnector):
    channel = "devto"


class HashnodeConnector(StubConnector):
    channel = "hashnode"


class MediumConnector(StubConnector):
    channel = "medium"


class GistConnector(StubConnector):
    channel = "gist"


