"""Application configuration."""

from __future__ import annotations

import os


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///gestium.db")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENV = os.getenv("FLASK_ENV", "development")
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
