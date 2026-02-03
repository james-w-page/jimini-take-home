"""Tests for in-memory storage"""

import pytest
from datetime import datetime
from app.storage.in_memory import InMemoryStorage
from app.models.encounter import EncounterCreate, EncounterType, EncounterFilter


def test_create_encounter():
    """Test creating an encounter"""
    storage = InMemoryStorage()
    
    encounter_data = EncounterCreate(
        patient_id="pat_123",
        provider_id="prov_456",
        encounter_date=datetime.utcnow(),
        encounter_type=EncounterType.INITIAL_ASSESSMENT,
        clinical_data={"notes": "Initial assessment"},
    )
    
    encounter = storage.create_encounter(encounter_data, created_by="user_1")
    
    assert encounter.encounter_id is not None
    assert encounter.patient_id == "pat_123"
    assert encounter.created_by == "user_1"
    assert encounter.created_at is not None


def test_get_encounter():
    """Test retrieving an encounter"""
    storage = InMemoryStorage()
    
    encounter_data = EncounterCreate(
        patient_id="pat_123",
        provider_id="prov_456",
        encounter_date=datetime.utcnow(),
        encounter_type=EncounterType.INITIAL_ASSESSMENT,
    )
    
    created = storage.create_encounter(encounter_data, created_by="user_1")
    retrieved = storage.get_encounter(created.encounter_id)
    
    assert retrieved is not None
    assert retrieved.encounter_id == created.encounter_id


def test_list_encounters_with_filters():
    """Test filtering encounters"""
    storage = InMemoryStorage()
    
    # Create multiple encounters
    for i in range(3):
        encounter_data = EncounterCreate(
            patient_id=f"pat_{i}",
            provider_id="prov_456",
            encounter_date=datetime.utcnow(),
            encounter_type=EncounterType.INITIAL_ASSESSMENT,
        )
        storage.create_encounter(encounter_data, created_by="user_1")
    
    # Filter by patient
    filters = EncounterFilter(patient_id="pat_0")
    results = storage.list_encounters(filters)
    
    assert len(results) == 1
    assert results[0].patient_id == "pat_0"
