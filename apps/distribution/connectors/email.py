
from __future__ import annotations

from . import StubConnector


class MailchimpConnector(StubConnector):
    channel = "mailchimp"


class SendGridConnector(StubConnector):
    channel = "sendgrid"


class SubstackConnector(StubConnector):
    channel = "substack"


