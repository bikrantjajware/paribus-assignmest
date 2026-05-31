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