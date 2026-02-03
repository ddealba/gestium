"""WSGI entrypoint for gunicorn and Flask CLI."""

from app import create_app

app = create_app()
