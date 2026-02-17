"""Filesystem storage helpers for documents."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, NotFound
from werkzeug.utils import secure_filename


_EXTENSION_TO_CONTENT_TYPE = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def _document_storage_root() -> Path:
    return Path(current_app.config["DOCUMENT_STORAGE_ROOT"]).resolve()


def _guess_extension(file: FileStorage) -> str:
    source_name = secure_filename(file.filename or "")
    if "." in source_name:
        ext = source_name.rsplit(".", 1)[1].lower()
        if ext:
            return ext

    content_type = (file.mimetype or "").lower()
    for extension, mime in _EXTENSION_TO_CONTENT_TYPE.items():
        if content_type == mime:
            return extension
    raise BadRequest("invalid_file_extension")


def save_upload(
    file: FileStorage,
    client_id: str,
    company_id: str,
    case_id: str,
) -> tuple[str, int, str | None, str]:
    """Save uploaded file to tenant-safe path under configured root."""
    original_filename = secure_filename(file.filename or "")
    if not original_filename:
        raise BadRequest("invalid_filename")

    extension = _guess_extension(file)
    unique_filename = f"{uuid4()}.{extension}"

    root_path = _document_storage_root()
    target_directory = root_path / str(client_id) / str(company_id) / str(case_id)
    target_directory.mkdir(parents=True, exist_ok=True)

    full_path = target_directory / unique_filename
    file.save(full_path)
    size_bytes = full_path.stat().st_size
    storage_path = str(full_path.relative_to(root_path))

    return storage_path, size_bytes, file.mimetype, original_filename


def open_file(storage_path: str) -> tuple[Path, str]:
    """Return validated file path and filename for streaming/download."""
    root_path = _document_storage_root()
    target_path = (root_path / storage_path).resolve()

    if root_path not in target_path.parents and target_path != root_path:
        raise BadRequest("invalid_storage_path")
    if not target_path.exists() or not target_path.is_file():
        raise NotFound("file_not_found")

    return target_path, target_path.name
