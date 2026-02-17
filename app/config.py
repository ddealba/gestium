"""Application configuration."""

from __future__ import annotations

import os


def _parse_allowed_document_mime(raw_value: str) -> tuple[str, ...]:
    """Parse allowed document mime/extensions from env var."""
    values = [value.strip().lower() for value in raw_value.split(",") if value.strip()]
    if not values:
        values = ["pdf", "png", "jpg"]
    return tuple(values)


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///gestium.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ALLOW_X_CLIENT_ID_HEADER = os.getenv("ALLOW_X_CLIENT_ID_HEADER", "false").lower() == "true"
    ENV = os.getenv("FLASK_ENV", "development")
    DOCUMENT_STORAGE_ROOT = os.getenv("DOCUMENT_STORAGE_ROOT", "/data/documents")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))
    ALLOWED_DOCUMENT_MIME = _parse_allowed_document_mime(
        os.getenv("ALLOWED_DOCUMENT_MIME", "pdf,png,jpg")
    )
    DEBUG = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    ENV = "development"
    DEBUG = True


class TestingConfig(BaseConfig):
    ENV = "testing"
    TESTING = True


class ProductionConfig(BaseConfig):
    ENV = "production"
    DEBUG = False


def get_config(config_name: str) -> type[BaseConfig]:
    """Return configuration class by name."""
    normalized_name = config_name.lower()
    config_map = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }
    return config_map.get(normalized_name, DevelopmentConfig)
