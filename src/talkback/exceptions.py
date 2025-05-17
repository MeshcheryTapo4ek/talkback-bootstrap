"""
Exceptions for py-rtsp-talkback.
"""

from __future__ import annotations


class TalkBackError(Exception):
    """Base class for all talk-back-related errors."""


class RTSPHandshakeError(TalkBackError):
    """Any error during the multi-step RTSP handshake."""


class RTSPAuthError(TalkBackError):
    """Digest-auth challenge missing or credentials not supplied."""
