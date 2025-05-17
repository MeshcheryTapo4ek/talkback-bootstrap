"""
talkback-bootstrap: minimal back-channel initiator for ONVIF/RTSP cameras.
"""

from importlib.metadata import version as _v

from .initiator import TalkBackInitiator

__all__ = ["TalkBackInitiator"]
__version__: str = _v("talkback-bootstrap")  # populated by packaging
