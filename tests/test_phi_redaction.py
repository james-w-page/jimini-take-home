"""Tests for PHI redaction utilities"""

import pytest
from app.core.phi_redaction import redact_phi, redact_dict, sanitize_error_message


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


def test_redact_dict_patient_id():
    """Test redaction of PHI fields in dictionary"""
    data = {
        "patient_id": "pat_123",
        "encounter_id": "enc_456",
        "provider_id": "prov_789",
    }
    result = redact_dict(data)
    assert result["patient_id"] == "[REDACTED]"
    assert result["encounter_id"] == "enc_456"  # Not PHI
    assert result["provider_id"] == "prov_789"  # Not PHI


def test_sanitize_error_message():
    """Test error message sanitization"""
    error_msg = "Error processing patient pat_123 with email patient@example.com"
    result = sanitize_error_message(error_msg)
    assert "pat_123" not in result
    assert "patient@example.com" not in result
    assert "[REDACTED]" in result
