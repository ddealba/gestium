"""Application factory and app initialization."""

from importlib import import_module
import pkgutil
import os

from flask import Flask

from app.common.errors import register_error_handlers
from app.config import get_config
from app.extensions import init_extensions


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    resolved_config = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(get_config(resolved_config))

    init_extensions(app)
    _register_module_blueprints(app)
    register_error_handlers(app)

    return app


def _register_module_blueprints(app: Flask) -> None:
    """Auto-discover and register blueprints from app.modules.* packages."""
    import app.modules as modules_pkg

    for module_info in pkgutil.iter_modules(modules_pkg.__path__):
        module_name = f"{modules_pkg.__name__}.{module_info.name}"
        module = import_module(module_name)
        blueprint = getattr(module, "bp", None)
        if blueprint is not None:
            app.register_blueprint(blueprint)
