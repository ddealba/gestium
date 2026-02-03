import os
import sys

import pytest


@pytest.fixture()
def app(monkeypatch):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("FLASK_ENV", "testing")

    from app import create_app

    return create_app("testing")


@pytest.fixture()
def client(app):
    return app.test_client()
