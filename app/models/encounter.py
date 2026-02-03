"""Encounter data models"""

from datetime import datetime
from typing import Any, Dict, Optional
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

    patient_id: str = Field(..., description="Patient identifier (PHI)", min_length=1)
    provider_id: str = Field(..., description="Provider/therapist identifier", min_length=1)
    encounter_date: datetime = Field(..., description="Date and time of the encounter")
    encounter_type: EncounterType = Field(..., description="Type of encounter")
    clinical_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSON structure for notes, observations, assessments",
    )

    @field_validator("patient_id", "provider_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate that IDs are not empty and don't contain only whitespace"""
        if not v or not v.strip():
            raise ValueError("ID cannot be empty or whitespace only")
        return v.strip()

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

    encounter_id: str = Field(..., description="Unique encounter identifier")
    created_at: datetime = Field(..., description="When the record was created")
    updated_at: datetime = Field(..., description="When the record was last updated")
    created_by: str = Field(..., description="User who created the record")

    model_config = {"json_schema_extra": {"example": {
        "encounter_id": "enc_123456",
        "patient_id": "pat_789",
        "provider_id": "prov_456",
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

    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    provider_id: Optional[str] = Field(None, description="Filter by provider ID")
    encounter_type: Optional[EncounterType] = Field(None, description="Filter by encounter type")
    start_date: Optional[datetime] = Field(None, description="Start of date range")
    end_date: Optional[datetime] = Field(None, description="End of date range")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate that end_date is after start_date if both are provided"""
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v
