from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from enum import Enum


class HospitalStatus(str, Enum):
    CREATED = "created"
    CREATED_AND_ACTIVATED = "created_and_activated"
    FAILED = "failed"


class HospitalRow(BaseModel):
    """Represents a single hospital record parsed from the CSV."""

    name: str = Field(..., min_length=1, description="name of the hospital")
    address: str = Field(..., min_length=1, description="address of the hospital")
    row: int = Field(..., description="row number of csv sheet uploaded")
    phone: Optional[str] = Field(None, description="Contact number")

    @field_validator("name", "address", "phone", mode="before")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        return stripped if stripped else None


class RowError(BaseModel):
    """Details of a single validation failure."""

    row: int
    errors: List[str]


class HospitalCreated(BaseModel):
    """Details of a single hospital record created from the CSV."""
    row: int
    hospital_id: int
    name: str
    status: HospitalStatus


class BulkUploadResponse(BaseModel):
    """Top-level response body for POST /hospitals/bulk."""

    batch_id: str = Field(..., description="unique id for uploaded file")
    total_hospitals: int = Field(..., description="Number of hospitals in csv")
    processed_hospitals: int = Field(..., description="Number of rows that passed validation")
    failed_hospitals: int = Field(..., description="Number of rows that failed validation")
    processing_time_seconds: int = Field(..., description="total seconds taken to process the file")
    batch_activated: bool = Field(..., description="Is the batch activated")
    hospitals: List[HospitalCreated] = Field(..., description="details of created hospitals")