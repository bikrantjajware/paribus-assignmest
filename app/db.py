from __future__ import annotations
from app.schemas import HospitalStatus
from datetime import datetime
from typing import Optional

HOSPITALS = {

}

class DBHospital:
    def __init__(self, 
                id: int,
                name: str,
                address: str,
                batch_id: str,
                status: str,
                created_at: datetime,
                row: int,
                active: bool,
                phone: Optional[str] = None):
        self.id = id
        self.name = name
        self.address = address
        self.phone = phone
        self.batch_id = batch_id
        self.status = status
        self.created_at = created_at
        self.row = row
        self.active = active


    def save(self):
        HOSPITALS[self.id] = self
        return self
    
    @staticmethod
    def get_hospital_by_id(hospital_id: int) -> Optional["DBHospital"]:
        return HOSPITALS.get(hospital_id)
    
    @staticmethod
    def activate_hospitals_in_batch(batch_id: str):
        for hospital in HOSPITALS.values():
            if hospital.batch_id == batch_id:
                hospital.status = HospitalStatus.CREATED_AND_ACTIVATED.value
                hospital.active = True


class BatchStore:
    _store: dict[str, dict] = {}
    current_batch_id: Optional[str] = None

    @classmethod
    def create(cls, batch_id: str, total_hospitals: int, row_errors: int) -> None:
        cls._store[batch_id] = {
            "started_at": datetime.utcnow(),
            "total_hospitals": total_hospitals,
            "processed_hospitals": 0,
            "row_errors": row_errors,
            "batch_activated": False,
            "hospitals": [],
            "end_time": None
        }

    @classmethod
    def append_hospital(cls, batch_id: str, hospital_entry: dict) -> None:
        cls._store[batch_id]["hospitals"].append(hospital_entry)
        cls._store[batch_id]["processed_hospitals"] += 1

    @classmethod
    def set_activated(cls, batch_id: str, activated: bool) -> None:
        cls._store[batch_id]["batch_activated"] = activated
    
    @classmethod
    def set_end_time(cls, batch_id: str) -> None:
        cls._store[batch_id]["end_time"] = datetime.utcnow()

    @classmethod
    def set_current(cls, batch_id: str) -> None:
        cls.current_batch_id = batch_id

    @classmethod
    def get_current(cls) -> Optional[str]:
        return cls.current_batch_id

    @classmethod
    def clear_current(cls) -> None:
        cls.current_batch_id = None

    @classmethod
    def get(cls, batch_id: str) -> Optional[dict]:
        return cls._store.get(batch_id)