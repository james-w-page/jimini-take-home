"""Tests for PHI redaction utilities"""

import pytest
import logging
from uuid import UUID
from app.core.phi_redaction import (
    redact_phi,
    redact_dict,
    sanitize_error_message,
    log_safely,
    PHI_FIELDS,
    APPROVED_UUID_FIELDS,
)


def test_redact_phi_ssn():
    """Test redaction of SSN patterns"""
    text = "Patient SSN: 123-45-6789"
    result = redact_phi(text)
    assert "123-45-6789" not in result
    assert "[REDACTED]" in result


def test_redact_phi_email():
    """Test redaction of email addresses"""
    text = "Contact: patient@example.com"
    result = redact_phi(text)
    assert "patient@example.com" not in result
    assert "[REDACTED]" in result


def test_redact_phi_uuids_in_message():
    """Test that UUIDs in message text are scrubbed"""
    text = "Encounter 550e8400-e29b-41d4-a716-446655440000 created for patient 550e8400-e29b-41d4-a716-446655440001"
    result = redact_phi(text)
    assert "550e8400-e29b-41d4-a716-446655440000" not in result
    assert "550e8400-e29b-41d4-a716-446655440001" not in result
    assert "[REDACTED-UUID]" in result


def test_redact_phi_mixed_content():
    """Test redaction of mixed PHI content"""
    text = "Patient 550e8400-e29b-41d4-a716-446655440000 (SSN: 123-45-6789) contacted at patient@example.com"
    result = redact_phi(text)
    assert "550e8400-e29b-41d4-a716-446655440000" not in result
    assert "123-45-6789" not in result
    assert "patient@example.com" not in result
    assert "[REDACTED-UUID]" in result
    assert "[REDACTED]" in result


def test_redact_dict_removes_phi_fields():
    """Test that PHI fields are completely removed from dictionaries"""
    data = {
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",
        "patient_name": "John Doe",
        "patient_email": "john@example.com",
        "encounter_id": "750e8400-e29b-41d4-a716-446655440000",
        "user_id": "850e8400-e29b-41d4-a716-446655440000",
        "notes": "Some notes",
    }
    result = redact_dict(data)
    
    # PHI fields should be completely removed
    assert "patient_id" not in result
    assert "patient_name" not in result
    assert "patient_email" not in result
    
    # Approved UUID fields should be preserved
    assert "encounter_id" in result
    assert result["encounter_id"] == "750e8400-e29b-41d4-a716-446655440000"
    assert "user_id" in result
    assert result["user_id"] == "850e8400-e29b-41d4-a716-446655440000"
    
    # Other non-PHI fields should be preserved
    assert "notes" in result
    assert result["notes"] == "Some notes"


def test_redact_dict_preserves_approved_uuid_fields():
    """Test that approved UUID fields preserve their UUID values"""
    data = {
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",  # PHI - removed
        "encounter_id": "750e8400-e29b-41d4-a716-446655440000",  # Approved - preserved
        "user_id": "850e8400-e29b-41d4-a716-446655440000",  # Approved - preserved
        "provider_id": "950e8400-e29b-41d4-a716-446655440000",  # Approved - preserved
        "organization_id": "a50e8400-e29b-41d4-a716-446655440000",  # Approved - preserved
        "event_id": "b50e8400-e29b-41d4-a716-446655440000",  # Approved - preserved
        "resource_id": "c50e8400-e29b-41d4-a716-446655440000",  # Approved - preserved
    }
    result = redact_dict(data)
    
    # PHI field removed
    assert "patient_id" not in result
    
    # All approved UUID fields preserved with their UUIDs
    assert result["encounter_id"] == "750e8400-e29b-41d4-a716-446655440000"
    assert result["user_id"] == "850e8400-e29b-41d4-a716-446655440000"
    assert result["provider_id"] == "950e8400-e29b-41d4-a716-446655440000"
    assert result["organization_id"] == "a50e8400-e29b-41d4-a716-446655440000"
    assert result["event_id"] == "b50e8400-e29b-41d4-a716-446655440000"
    assert result["resource_id"] == "c50e8400-e29b-41d4-a716-446655440000"


def test_redact_dict_nested_structures():
    """Test redaction in nested dictionaries and lists"""
    data = {
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",
        "encounter": {
            "encounter_id": "750e8400-e29b-41d4-a716-446655440000",
            "patient_id": "550e8400-e29b-41d4-a716-446655440001",  # PHI in nested dict
        },
        "events": [
            {"event_id": "850e8400-e29b-41d4-a716-446655440000", "patient_id": "550e8400-e29b-41d4-a716-446655440002"},
            {"event_id": "850e8400-e29b-41d4-a716-446655440001", "user_id": "950e8400-e29b-41d4-a716-446655440000"},
        ],
    }
    result = redact_dict(data)
    
    # Top-level PHI field removed
    assert "patient_id" not in result
    
    # Nested PHI fields removed
    assert "patient_id" not in result["encounter"]
    assert result["encounter"]["encounter_id"] == "750e8400-e29b-41d4-a716-446655440000"
    
    # List items processed
    assert len(result["events"]) == 2
    assert "patient_id" not in result["events"][0]
    assert result["events"][0]["event_id"] == "850e8400-e29b-41d4-a716-446655440000"
    assert result["events"][1]["user_id"] == "950e8400-e29b-41d4-a716-446655440000"


def test_sanitize_error_message():
    """Test error message sanitization"""
    error_msg = "Error processing patient 550e8400-e29b-41d4-a716-446655440000 with email patient@example.com"
    result = sanitize_error_message(error_msg)
    assert "550e8400-e29b-41d4-a716-446655440000" not in result
    assert "patient@example.com" not in result
    assert "[REDACTED-UUID]" in result
    assert "[REDACTED]" in result


def test_sanitize_error_message_with_context():
    """Test error message sanitization with context"""
    error_msg = "Error occurred"
    context = {
        "patient_id": "550e8400-e29b-41d4-a716-446655440000",
        "encounter_id": "750e8400-e29b-41d4-a716-446655440000",
    }
    result = sanitize_error_message(error_msg, context)
    assert "[Context contains PHI - redacted]" in result


def test_log_safely_scrubs_uuids_in_message():
    """Test that log_safely scrubs UUIDs from message text"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    log_safely(
        logger,
        logging.INFO,
        "Encounter 550e8400-e29b-41d4-a716-446655440000 created for patient 550e8400-e29b-41d4-a716-446655440001",
    )
    
    output = log_capture.getvalue()
    assert "550e8400-e29b-41d4-a716-446655440000" not in output
    assert "550e8400-e29b-41d4-a716-446655440001" not in output
    assert "[REDACTED-UUID]" in output


def test_log_safely_preserves_approved_uuid_fields():
    """Test that log_safely preserves UUIDs in approved fields"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    encounter_id = UUID("750e8400-e29b-41d4-a716-446655440000")
    user_id = UUID("850e8400-e29b-41d4-a716-446655440000")
    
    log_safely(
        logger,
        logging.INFO,
        "Encounter created",
        encounter_id=encounter_id,
        user_id=user_id,
    )
    
    output = log_capture.getvalue()
    # Approved UUID fields should be preserved
    assert "encounter_id=750e8400-e29b-41d4-a716-446655440000" in output
    assert "user_id=850e8400-e29b-41d4-a716-446655440000" in output


def test_log_safely_removes_phi_fields():
    """Test that log_safely removes PHI fields completely"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    log_safely(
        logger,
        logging.INFO,
        "Processing",
        patient_id="550e8400-e29b-41d4-a716-446655440000",
        encounter_id=UUID("750e8400-e29b-41d4-a716-446655440000"),
    )
    
    output = log_capture.getvalue()
    # PHI field should not appear in output
    assert "patient_id" not in output
    assert "550e8400-e29b-41d4-a716-446655440000" not in output
    
    # Approved field should be preserved
    assert "encounter_id=750e8400-e29b-41d4-a716-446655440000" in output


def test_log_safely_scrubs_uuids_in_args():
    """Test that UUIDs in args are scrubbed"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    uuid_arg = UUID("550e8400-e29b-41d4-a716-446655440000")
    log_safely(logger, logging.INFO, "Processing %s", uuid_arg)
    
    output = log_capture.getvalue()
    assert "550e8400-e29b-41d4-a716-446655440000" not in output
    assert "[REDACTED-UUID]" in output


def test_log_safely_scrubs_uuids_in_non_approved_kwargs():
    """Test that UUIDs in non-approved kwargs are not included in logs"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.INFO)
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    log_safely(
        logger,
        logging.INFO,
        "Processing",
        some_other_id=UUID("550e8400-e29b-41d4-a716-446655440000"),  # Not approved - should not appear
        encounter_id=UUID("750e8400-e29b-41d4-a716-446655440000"),  # Approved - should be preserved
    )
    
    output = log_capture.getvalue()
    # Non-approved UUID field should not appear in output
    assert "some_other_id" not in output
    assert "550e8400-e29b-41d4-a716-446655440000" not in output
    
    # Approved UUID should be preserved
    assert "encounter_id=750e8400-e29b-41d4-a716-446655440000" in output


def test_log_safely_with_exc_info():
    """Test that log_safely handles exc_info correctly and redacts UUIDs from traceback"""
    logger = logging.getLogger("test")
    logger.setLevel(logging.ERROR)
    
    # Use PHI redacting formatter to ensure tracebacks are redacted
    from app.core.phi_redaction import PHIRedactingFormatter
    
    # Capture log output
    import io
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(PHIRedactingFormatter("%(message)s\n%(exc_text)s"))
    logger.addHandler(handler)
    
    try:
        raise ValueError("Test error with UUID 550e8400-e29b-41d4-a716-446655440000")
    except ValueError:
        log_safely(logger, logging.ERROR, "Error occurred", exc_info=True)
    
    output = log_capture.getvalue()
    # UUID in exception message should be scrubbed
    assert "550e8400-e29b-41d4-a716-446655440000" not in output
    assert "[REDACTED-UUID]" in output or "Error occurred" in output


def test_redact_phi_case_insensitive_uuid():
    """Test that UUID redaction is case-insensitive"""
    text = "Encounter 550E8400-E29B-41D4-A716-446655440000 created"
    result = redact_phi(text)
    assert "550E8400-E29B-41D4-A716-446655440000" not in result
    assert "[REDACTED-UUID]" in result


def test_redact_dict_all_phi_field_variations():
    """Test that all PHI field name variations are removed"""
    data = {
        "patient_id": "value1",
        "patientId": "value2",
        "patient_name": "value3",
        "patientName": "value4",
        "patient_email": "value5",
        "patientEmail": "value6",
        "ssn": "value7",
        "date_of_birth": "value8",
        "dateOfBirth": "value9",
        "encounter_id": "750e8400-e29b-41d4-a716-446655440000",  # Should be preserved
    }
    result = redact_dict(data)
    
    # All PHI field variations should be removed
    assert "patient_id" not in result
    assert "patientId" not in result
    assert "patient_name" not in result
    assert "patientName" not in result
    assert "patient_email" not in result
    assert "patientEmail" not in result
    assert "ssn" not in result
    assert "date_of_birth" not in result
    assert "dateOfBirth" not in result
    
    # Approved field should be preserved
    assert "encounter_id" in result
    assert result["encounter_id"] == "750e8400-e29b-41d4-a716-446655440000"


def test_redact_dict_empty_dict():
    """Test redaction of empty dictionary"""
    result = redact_dict({})
    assert result == {}


def test_redact_dict_none_values():
    """Test redaction handles None values"""
    data = {
        "patient_id": None,
        "encounter_id": "750e8400-e29b-41d4-a716-446655440000",
        "notes": None,
    }
    result = redact_dict(data)
    
    # PHI field with None should still be removed
    assert "patient_id" not in result
    
    # Other fields preserved
    assert "encounter_id" in result
    assert "notes" in result
    assert result["notes"] is None
