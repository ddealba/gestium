"""App extensions registry."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)


class JsonLogFormatter(logging.Formatter):
    """Basic structured logging formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        return json.dumps(payload)


def _configure_logging(app: Flask) -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)
    app.logger.handlers = root_logger.handlers


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    _configure_logging(app)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
