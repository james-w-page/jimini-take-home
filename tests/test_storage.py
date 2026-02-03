"""Tests for in-memory storage"""

import pytest
from datetime import datetime, timezone
from uuid import UUID
from app.storage.in_memory import InMemoryStorage
from app.models.encounter import EncounterCreate, EncounterType, EncounterFilter
from app.core.constants import get_patient_ids, get_provider_ids


def test_create_encounter():
    """Test creating an encounter"""
    storage = InMemoryStorage()
    
    # Get valid patient and provider IDs
    patient_id = UUID(get_patient_ids()[0])
    provider_id = UUID(get_provider_ids()[0])
    user_id = UUID("850e8400-e29b-41d4-a716-446655440000")  # Admin user
    
    encounter_data = EncounterCreate(
        patient_id=patient_id,
        provider_id=provider_id,
        encounter_date=datetime.now(timezone.utc),
        encounter_type=EncounterType.INITIAL_ASSESSMENT,
        clinical_data={"notes": "Initial assessment"},
    )
    
    encounter = storage.create_encounter(encounter_data, created_by=user_id)
    
    assert encounter.encounter_id is not None
    assert isinstance(encounter.encounter_id, UUID)
    assert encounter.patient_id == patient_id
    assert encounter.created_by == user_id
    assert encounter.created_at is not None


def test_get_encounter():
    """Test retrieving an encounter"""
    storage = InMemoryStorage()
    
    # Get valid patient and provider IDs
    patient_id = UUID(get_patient_ids()[0])
    provider_id = UUID(get_provider_ids()[0])
    user_id = UUID("850e8400-e29b-41d4-a716-446655440000")  # Admin user
    
    encounter_data = EncounterCreate(
        patient_id=patient_id,
        provider_id=provider_id,
        encounter_date=datetime.now(timezone.utc),
        encounter_type=EncounterType.INITIAL_ASSESSMENT,
    )
    
    created = storage.create_encounter(encounter_data, created_by=user_id)
    retrieved = storage.get_encounter(created.encounter_id)
    
    assert retrieved is not None
    assert retrieved.encounter_id == created.encounter_id


def test_list_encounters_with_filters():
    """Test filtering encounters"""
    storage = InMemoryStorage()
    
    # Get valid patient and provider IDs
    patients = [UUID(pid) for pid in get_patient_ids()[:3]]
    provider_id = UUID(get_provider_ids()[0])
    user_id = UUID("850e8400-e29b-41d4-a716-446655440000")  # Admin user
    
    # Create multiple encounters
    for i in range(3):
        encounter_data = EncounterCreate(
            patient_id=patients[i],
            provider_id=provider_id,
            encounter_date=datetime.now(timezone.utc),
            encounter_type=EncounterType.INITIAL_ASSESSMENT,
        )
        storage.create_encounter(encounter_data, created_by=user_id)
    
    # Filter by patient
    filters = EncounterFilter(patient_id=patients[0])
    results = storage.list_encounters(filters)
    
    assert len(results) == 1
    assert results[0].patient_id == patients[0]
