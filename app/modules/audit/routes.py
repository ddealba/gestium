"""Audit routes are mounted in admin module; kept for blueprint auto-discovery compatibility."""

from flask import Blueprint

bp = Blueprint("audit", __name__)
