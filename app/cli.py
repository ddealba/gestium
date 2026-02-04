"""Application CLI commands."""

from __future__ import annotations

import click
from flask import Flask

from app.extensions import db
from app.models.client import Client


def register_cli(app: Flask) -> None:
    """Register CLI commands on the Flask app."""

    @app.cli.command("seed")
    def seed() -> None:
        """Seed the database with initial data."""
        seed_default_client()

    @app.cli.command("seed_clients")
    def seed_clients() -> None:
        """Seed the database with initial client data."""
        seed_default_client()


def seed_default_client() -> None:
    """Create the default client if it does not exist."""
    existing_client = Client.query.filter_by(name="Default Client").first()
    if existing_client:
        click.echo("Default Client already exists. Skipping.")
        return

    client = Client(name="Default Client", status="active", plan="mvp")
    db.session.add(client)
    db.session.commit()
    click.echo("Default Client created.")
