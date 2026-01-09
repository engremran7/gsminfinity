from __future__ import annotations

from . import LoggingConnector


class DevtoConnector(LoggingConnector):
    channel = "devto"


class HashnodeConnector(LoggingConnector):
    channel = "hashnode"


class MediumConnector(LoggingConnector):
    channel = "medium"


class GistConnector(LoggingConnector):
    channel = "gist"
