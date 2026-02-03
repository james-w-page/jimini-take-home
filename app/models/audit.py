"""Audit trail models"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class AuditEvent(BaseModel):
    """Model for audit trail events"""

    event_id: UUID = Field(..., description="Unique event identifier (UUID)")
    event_type: str = Field(..., description="Type of event (e.g., 'encounter_created', 'encounter_accessed')")
    resource_type: str = Field(..., description="Type of resource (e.g., 'encounter')")
    resource_id: str = Field(..., description="ID of the resource accessed")
    user_id: UUID = Field(..., description="User who performed the action (UUID)")
    timestamp: datetime = Field(..., description="When the event occurred")
    ip_address: Optional[str] = Field(None, description="IP address of the request")
    user_agent: Optional[str] = Field(None, description="User agent of the request")
    additional_data: Optional[dict] = Field(
        default_factory=dict,
        description="Additional context about the event",
    )

    @field_validator("event_id", "user_id", mode="before")
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

    model_config = {"json_schema_extra": {"example": {
        "event_id": "550e8400-e29b-41d4-a716-446655440010",
        "event_type": "encounter_accessed",
        "resource_type": "encounter",
        "resource_id": "550e8400-e29b-41d4-a716-446655440011",
        "user_id": "750e8400-e29b-41d4-a716-446655440010",
        "timestamp": "2024-01-15T10:30:00Z",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "additional_data": {}
    }}}


class AuditFilter(BaseModel):
    """Model for filtering audit events"""

    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    user_id: Optional[UUID] = Field(None, description="Filter by user ID (UUID)")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    start_date: Optional[datetime] = Field(None, description="Start of date range")
    end_date: Optional[datetime] = Field(None, description="End of date range")

    @field_validator("user_id", mode="before")
    @classmethod
    def validate_uuid_optional(cls, v) -> Optional[UUID]:
        """Validate that user_id is a valid UUID if provided"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {v}")
        if isinstance(v, UUID):
            return v
        raise ValueError(f"user_id must be a UUID, got {type(v)}")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate that end_date is after start_date if both are provided"""
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v
