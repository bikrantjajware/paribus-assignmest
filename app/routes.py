from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request
from werkzeug.datastructures import FileStorage

from app.services.hospital_service import process_bulk_upload

logger = logging.getLogger(__name__)

hospitals_bp = Blueprint("hospitals", __name__, url_prefix="/hospitals")

_ALLOWED_CONTENT_TYPES = {"text/csv", "application/csv"}


@hospitals_bp.route("/bulk", methods=["POST"])
def bulk_upload():
    """
    Request: accepts a Multipart form data with CSV file with Columns name, address, phone (phone is optional)
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request. Send the CSV as 'file' field."}), 400

    uploaded_file: FileStorage = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({"error": "No file selected."}), 400

    content_type = (uploaded_file.content_type or "").split(";")[0].strip().lower()
    filename_lower = (uploaded_file.filename or "").lower()

    if content_type not in _ALLOWED_CONTENT_TYPES and not filename_lower.endswith(".csv"):
        return (
            jsonify({"error": f"Unsupported file type '{content_type}'. Please upload a CSV file."}),
            415,
        )
    try:
        response, _row_errors = process_bulk_upload(uploaded_file)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except UnicodeDecodeError:
        return jsonify({"error": "Could not decode the file. Ensure it is saved as UTF-8."}), 400
    except RuntimeError as exc:
        logger.exception(f'failed to process the file {exc}')
        return jsonify({"error": "something went wrong processing the file."}), 500

    return jsonify(response.model_dump()), 200
