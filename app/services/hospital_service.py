from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Tuple, Optional

from werkzeug.datastructures import FileStorage

from app.utils import hospital_utils
from app.schemas import BulkUploadResponse, HospitalRow, HospitalStatus, RowError
from app.utils.file_utils import parse_csv_upload
from app.db import BatchStore

logger = logging.getLogger(__name__)


def process_bulk_upload(uploaded_file: FileStorage) -> Tuple[BulkUploadResponse, list[RowError]]:
    """
    Orchestrates the full bulk-upload flow:
      1. Parse and validate the CSV rows.
      2. Generate a batch identifier.
      3. Persist each valid hospital via the integration layer.
      4. Return a structured response plus the list of row-level validation errors.

    Raises:
        ValueError:       If the file is empty or has no data rows (bubble up to the route for 400).
        UnicodeDecodeError: If the file cannot be decoded as UTF-8 (bubble up for 400).
        RuntimeError:     If any hospital cannot be persisted (bubble up for 500).
    """
    valid_rows, row_errors = parse_csv_upload(uploaded_file, HospitalRow)

    total = len(valid_rows) + len(row_errors)
    logger.info(
        "process_bulk_upload: processed %d rows – %d valid, %d invalid",
        total,
        len(valid_rows),
        len(row_errors),
    )
    logger.error(f'failed rows:{row_errors}')

    batch_id = str(uuid.uuid4())
    initial_status = HospitalStatus.CREATED.value

    # save initial info for batch
    BatchStore.create(batch_id, total_hospitals=total, row_errors=len(row_errors))
    BatchStore.set_current(batch_id)
    created_hospitals = []
    batch_activated = False
    try:
        created_hospitals = _persist_hospitals(valid_rows, batch_id, initial_status)
    except RuntimeError as e:
        pass

    if len(created_hospitals) == total:
        batch_activated = hospital_utils.activate_hospitals_in_batch(batch_id)
        BatchStore.set_activated(batch_id, batch_activated)
    
    BatchStore.set_end_time(batch_id)
    batch_entry = BatchStore.get(batch_id)
    BatchStore.clear_current()
    response = BulkUploadResponse(
        batch_id=batch_id,
        total_hospitals=total,
        processed_hospitals=len(valid_rows),
        failed_hospitals=len(row_errors),
        processing_time_seconds=int(((batch_entry.get("end_time") or datetime.utcnow()) - batch_entry["started_at"]).total_seconds()),
        batch_activated=batch_activated,
        hospitals=created_hospitals,
    )
    return response, row_errors


def get_batch_status(batch_id: str) -> Optional[BulkUploadResponse]:
    entry = BatchStore.get(batch_id)
    if entry is None:
        return None

    elapsed = int(((entry.get("end_time") or datetime.utcnow()) - entry["started_at"]).total_seconds())

    return BulkUploadResponse(
        batch_id=batch_id,
        total_hospitals=entry["total_hospitals"],
        processed_hospitals=entry["processed_hospitals"],
        failed_hospitals=entry["row_errors"],
        processing_time_seconds=elapsed,
        batch_activated=entry["batch_activated"],
        hospitals=entry["hospitals"],
    )


def _persist_hospitals(
    valid_rows: list[HospitalRow],
    batch_id: str,
    status: str,
) -> list[dict]:
    """
    Returns:
        List of dicts describing each persisted hospital, ready for ``BulkUploadResponse.hospitals``.

    Raises:
        RuntimeError: Wraps any unexpected persistence error so the caller can map it to HTTP 500.
    """
    created: list[dict] = []

    for hospital in valid_rows:
        try:
            db_hospital = hospital_utils.create_hospital(hospital, batch_id, status)
            hospital_entry = {
                "row": db_hospital.row,
                "hospital_id": db_hospital.id,
                "name": db_hospital.name,
                "status": db_hospital.status
            }
            created.append(hospital_entry)

            # Keep the store in sync so status polls reflect real-time progress.
            BatchStore.append_hospital(batch_id, hospital_entry)

        except Exception as exc:
            logger.exception("Failed to persist hospital from row %d: %s", hospital.row, exc)
            raise RuntimeError(
                f"Failed to persist hospital '{hospital.name}' (row {hospital.row})."
            ) from exc

    return created
