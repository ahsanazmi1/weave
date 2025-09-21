"""
Configuration settings for Weave CloudEvents subscriber.
"""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database configuration
    database_url: str = "sqlite:///./weave_receipts.db"

    # Allowed CloudEvent types
    allowed_event_types: List[str] = [
        "ocn.orca.decision.v1",
        "ocn.orca.explanation.v1",
        "ocn.weave.audit.v1"
    ]

    # API configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Security settings
    api_key: Optional[str] = None
    enable_authentication: bool = False

    # Logging
    log_level: str = "INFO"

    # Trust Registry
    trust_registry_path: Optional[str] = None

    class Config:
        env_file = ".env"
        env_prefix = "WEAVE_"


# Global settings instance
settings = Settings()
