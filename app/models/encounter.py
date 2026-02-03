"""Encounter data models"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class EncounterType(str, Enum):
    """Valid encounter types"""

    INITIAL_ASSESSMENT = "initial_assessment"
    FOLLOW_UP = "follow_up"
    TREATMENT_SESSION = "treatment_session"
    CONSULTATION = "consultation"
    DISCHARGE = "discharge"


class EncounterBase(BaseModel):
    """Base encounter model with common fields"""

    patient_id: UUID = Field(..., description="Patient identifier (PHI) - must be a valid UUID")
    provider_id: UUID = Field(..., description="Provider/therapist identifier - must be a valid UUID")
    encounter_date: datetime = Field(..., description="Date and time of the encounter")
    encounter_type: EncounterType = Field(..., description="Type of encounter")
    clinical_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSON structure for notes, observations, assessments",
    )

    @field_validator("patient_id", "provider_id", mode="before")
    @classmethod
    def validate_uuid_format(cls, v) -> UUID:
        """Validate that IDs are valid UUIDs"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        if isinstance(v, UUID):
            return v
        raise ValueError(f"ID must be a UUID, got {type(v)}")

    @field_validator("clinical_data")
    @classmethod
    def validate_clinical_data(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate clinical data is a dictionary"""
        if not isinstance(v, dict):
            raise ValueError("clinical_data must be a dictionary")
        return v


class EncounterCreate(EncounterBase):
    """Model for creating a new encounter"""

    pass


class Encounter(EncounterBase):
    """Full encounter model with generated fields"""

    encounter_id: UUID = Field(..., description="Unique encounter identifier (UUID)")
    created_at: datetime = Field(..., description="When the record was created")
    updated_at: datetime = Field(..., description="When the record was last updated")
    created_by: UUID = Field(..., description="User who created the record (UUID)")

    @field_validator("created_by", mode="before")
    @classmethod
    def validate_created_by_uuid(cls, v) -> UUID:
        """Validate that created_by is a valid UUID"""
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        if isinstance(v, UUID):
            return v
        raise ValueError(f"created_by must be a UUID, got {type(v)}")

    model_config = {"json_schema_extra": {"example": {
        "encounter_id": "550e8400-e29b-41d4-a716-446655440010",
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",
        "provider_id": "750e8400-e29b-41d4-a716-446655440000",
        "encounter_date": "2024-01-15T10:30:00Z",
        "encounter_type": "initial_assessment",
        "clinical_data": {
            "chief_complaint": "Anxiety and stress",
            "mental_status": "Alert and oriented",
            "assessment": "Generalized anxiety disorder"
        },
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "created_by": "user_123"
    }}}


class EncounterFilter(BaseModel):
    """Model for filtering encounters"""

    patient_id: Optional[UUID] = Field(None, description="Filter by patient ID")
    provider_id: Optional[UUID] = Field(None, description="Filter by provider ID")
    encounter_type: Optional[EncounterType] = Field(None, description="Filter by encounter type")
    start_date: Optional[datetime] = Field(None, description="Start of date range")
    end_date: Optional[datetime] = Field(None, description="End of date range")

    @field_validator("patient_id", "provider_id", mode="before")
    @classmethod
    def validate_uuid_optional(cls, v) -> Optional[UUID]:
        """Validate that IDs are valid UUIDs if provided"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        if isinstance(v, UUID):
            return v
        raise ValueError(f"ID must be a UUID, got {type(v)}")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate that end_date is after start_date if both are provided"""
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v
