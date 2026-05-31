from __future__ import annotations
import logging

from app.db import DBHospital
from app.extensions import hospital_client
from app.schemas import HospitalRow

logger = logging.getLogger(__name__)


def create_hospital(hospital: HospitalRow, batch_id: str, status: str) -> DBHospital:
    logger.debug("Creating hospital via client: %s", hospital)
    created_hospital = hospital_client.create_hospital(hospital=hospital, batch_id=batch_id)
    logger.debug("External API response: %s", created_hospital)
    db_hospital = DBHospital(
        id=created_hospital["id"],
        name=created_hospital["name"],
        address=created_hospital["address"],
        batch_id=created_hospital["creation_batch_id"],
        status=status,
        created_at=created_hospital["created_at"],
        row=hospital.row,
        active=created_hospital["active"],
        phone=created_hospital["phone"]
        )
    db_hospital.save()
    return db_hospital