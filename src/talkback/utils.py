"""
Utility helpers:

* get_logger()   – project-wide singleton with optional dynamic level bump.
* parse_rtsp_url() – safe RTSP URL parsing into RTSPUrlParts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final
from urllib.parse import unquote, urlparse

from .settings import settings

# ─────────────── RTSP url parts ────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class RTSPUrlParts:
    username: str | None
    password: str | None
    host: str
    port: int
    path: str  # path without leading “/”


# ─────────────── Logging ───────────────────────────────────────────────────
_LOGGER: logging.Logger | None = None
_DEFAULT_LEVEL: Final[int] = getattr(
    logging, settings.log_level.upper(), logging.INFO
)


def _level_num(name: str) -> int:
    return getattr(logging, name.upper(), logging.INFO)


def get_logger(name: str = "talkback", *, level: str | None = None) -> logging.Logger:
    """
    Return the project singleton logger.  
    If *level* is supplied (e.g. ``"DEBUG"``) and is **more verbose** than the
    current level, the logger is bumped up.
    """
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = logging.getLogger(name)
        _LOGGER.setLevel(_DEFAULT_LEVEL)

        h = logging.StreamHandler()
        fmt = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
        h.setFormatter(logging.Formatter(fmt))
        _LOGGER.addHandler(h)
        _LOGGER.propagate = False

    if level and _level_num(level) < _LOGGER.level:  # DEBUG < INFO …
        _LOGGER.setLevel(_level_num(level))

    return _LOGGER


# ─────────────── URL parsing ───────────────────────────────────────────────
def parse_rtsp_url(url: str) -> RTSPUrlParts:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "rtsp":
        raise ValueError(f"Unsupported scheme (expect 'rtsp'): {url!r}")

    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    host = parsed.hostname or ""
    port = parsed.port or 554
    if not host:
        raise ValueError(f"Host missing in RTSP URL: {url!r}")

    return RTSPUrlParts(
        username=username,
        password=password,
        host=host,
        port=port,
        path=parsed.path.lstrip("/") or "",
    )
