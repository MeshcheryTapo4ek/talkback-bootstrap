"""
Centralised runtime configuration (one Settings per project).
"""

from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ─ Network ────────────────────────────────────────────────────────────
    rtsp_timeout: int = Field(
        5, description="TCP connect / read timeout in seconds"
    )
    default_client_port: int = Field(
        5000, description="UDP port used in SETUP (client_port N-N+1)"
    )

    # ─ Logging ────────────────────────────────────────────────────────────
    log_level: str = Field(
        "INFO",
        description="Default log level (DEBUG|INFO|WARNING|ERROR|CRITICAL)",
    )

    class Config:
        env_prefix = "TALKBACK_"  # e.g. TALKBACK_LOG_LEVEL=DEBUG


settings = Settings()  # singleton imported by helpers
