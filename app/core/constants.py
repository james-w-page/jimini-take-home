"""Constants for known patients and providers"""

from typing import Dict
from uuid import UUID

# Known patients (hard-coded for validation)
KNOWN_PATIENTS: Dict[str, Dict[str, str]] = {
    "550e8400-e29b-41d4-a716-446655440000": {
        "name": "Patient One",
        "status": "active",
    },
    "550e8400-e29b-41d4-a716-446655440001": {
        "name": "Patient Two",
        "status": "active",
    },
    "550e8400-e29b-41d4-a716-446655440002": {
        "name": "Patient Three",
        "status": "active",
    },
    "550e8400-e29b-41d4-a716-446655440003": {
        "name": "Patient Four",
        "status": "active",
    },
    "550e8400-e29b-41d4-a716-446655440004": {
        "name": "Patient Five",
        "status": "active",
    },
}

# Known providers (hard-coded for validation)
KNOWN_PROVIDERS: Dict[str, Dict[str, str]] = {
    "750e8400-e29b-41d4-a716-446655440000": {
        "name": "Dr. Smith",
        "specialty": "Psychiatry",
        "status": "active",
    },
    "750e8400-e29b-41d4-a716-446655440001": {
        "name": "Dr. Jones",
        "specialty": "Psychology",
        "status": "active",
    },
    "750e8400-e29b-41d4-a716-446655440002": {
        "name": "Dr. Williams",
        "specialty": "Therapy",
        "status": "active",
    },
    "750e8400-e29b-41d4-a716-446655440003": {
        "name": "Dr. Brown",
        "specialty": "Counseling",
        "status": "active",
    },
}


def is_valid_patient_id(patient_id: str) -> bool:
    """Check if a patient ID is valid (exists in known patients)"""
    try:
        # Validate UUID format
        UUID(patient_id)
        return patient_id in KNOWN_PATIENTS
    except (ValueError, TypeError):
        return False


def is_valid_provider_id(provider_id: str) -> bool:
    """Check if a provider ID is valid (exists in known providers)"""
    try:
        # Validate UUID format
        UUID(provider_id)
        return provider_id in KNOWN_PROVIDERS
    except (ValueError, TypeError):
        return False


def get_patient_ids() -> list[str]:
    """Get list of all valid patient IDs"""
    return list(KNOWN_PATIENTS.keys())


def get_provider_ids() -> list[str]:
    """Get list of all valid provider IDs"""
    return list(KNOWN_PROVIDERS.keys())
