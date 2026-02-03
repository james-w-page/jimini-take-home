"""PHI (Protected Health Information) redaction utilities for logs and error messages"""

import re
import logging
from typing import Any, Dict, List, Union
from functools import wraps
from uuid import UUID


# Patterns that might indicate PHI
PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format XXX-XX-XXXX
    r"\b\d{3}\.\d{2}\.\d{4}\b",  # SSN format XXX.XX.XXXX
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email addresses
    r"\b\d{3}-\d{3}-\d{4}\b",  # Phone numbers XXX-XXX-XXXX
    r"\b\(\d{3}\)\s?\d{3}-\d{4}\b",  # Phone numbers (XXX) XXX-XXXX
    r"\b\d{10}\b",  # 10-digit numbers (could be phone or ID)
]

# UUID pattern (matches standard UUID format)
UUID_PATTERN = r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"

# Fields that are known to contain PHI - these will be completely removed/redacted
PHI_FIELDS = {
    "patient_id",
    "patientId",
    "patient_name",
    "patientName",
    "patient_email",
    "patientEmail",
    "patient_phone",
    "patientPhone",
    "ssn",
    "social_security_number",
    "date_of_birth",
    "dateOfBirth",
    "dob",
    "address",
    "medical_record_number",
    "medicalRecordNumber",
}

# Approved fields that can contain UUIDs in log messages
APPROVED_UUID_FIELDS = {
    "user_id",
    "userId",
    "provider_id",
    "providerId",
    "organization_id",
    "organizationId",
    "encounter_id",
    "encounterId",
    "event_id",
    "eventId",
    "resource_id",
    "resourceId",
}


class PHIRedactingFormatter(logging.Formatter):
    """Custom logging formatter that redacts PHI from log messages"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record and redact PHI"""
        original_msg = super().format(record)
        return redact_phi(original_msg)


def redact_phi(text: str, approved_uuid_fields: set = None) -> str:
    """
    Redact PHI from text string.
    
    Replaces potential PHI with [REDACTED] markers.
    Scrubs all UUIDs from the message text, except those in approved fields.
    
    Args:
        text: Text string to redact
        approved_uuid_fields: Set of field names that are allowed to contain UUIDs
    
    Returns:
        Redacted text string
    """
    if not isinstance(text, str):
        text = str(text)

    # Redact patterns (SSN, email, phone, etc.)
    redacted = text
    for pattern in PHI_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    # Scrub all UUIDs from the message text
    # UUIDs should only appear in approved fields, not in the message text itself
    redacted = re.sub(UUID_PATTERN, "[REDACTED-UUID]", redacted, flags=re.IGNORECASE)

    return redacted


def redact_dict(data: Dict[str, Any], fields_to_redact: set = None) -> Dict[str, Any]:
    """
    Redact PHI from dictionary, replacing values of known PHI fields.
    
    Removes all fields in PHI_FIELDS completely.
    Approved UUID fields are preserved (user_id, provider_id, encounter_id, etc.).
    
    Args:
        data: Dictionary to redact
        fields_to_redact: Additional fields to redact (merged with PHI_FIELDS)
    
    Returns:
        New dictionary with PHI values redacted
    """
    if fields_to_redact is None:
        fields_to_redact = set()
    
    all_phi_fields = PHI_FIELDS | fields_to_redact
    redacted = {}
    
    for key, value in data.items():
        # Check if key indicates PHI
        key_lower = key.lower()
        is_phi_field = any(phi_field.lower() in key_lower for phi_field in all_phi_fields)
        
        # Remove PHI fields completely
        if is_phi_field:
            # Don't include PHI fields in the redacted output
            continue
        
        # Process value based on type
        if isinstance(value, dict):
            redacted[key] = redact_dict(value, fields_to_redact)
        elif isinstance(value, list):
            redacted[key] = [redact_dict(item, fields_to_redact) if isinstance(item, dict) else item 
                           for item in value]
        else:
            # Approved UUID fields and other non-PHI fields are preserved
            redacted[key] = value
    
    return redacted


def sanitize_error_message(error_msg: str, context: Dict[str, Any] = None) -> str:
    """
    Sanitize error messages to remove PHI.
    
    Scrubs all UUIDs from the message text. Only approved fields can contain UUIDs.
    
    Args:
        error_msg: Original error message
        context: Optional context dictionary that might contain PHI
    
    Returns:
        Sanitized error message safe for logging
    """
    # Redact patterns and UUIDs in the message itself
    sanitized = redact_phi(error_msg)
    
    # If context provided, check for PHI fields
    if context:
        # Redact context dictionary (removes PHI fields, preserves approved UUID fields)
        redacted_context = redact_dict(context)
        # Don't include full context in error message, just note if PHI was present
        if any(field in str(context).lower() for field in PHI_FIELDS):
            sanitized += " [Context contains PHI - redacted]"
    
    return sanitized


def log_safely(logger: logging.Logger, level: int, message: str, *args, **kwargs):
    """
    Safely log a message with PHI redaction.
    
    - Removes all fields in PHI_FIELDS
    - Scrubs all UUIDs from the message text
    - Only approved UUID fields (user_id, provider_id, encounter_id, etc.) can contain UUIDs
    
    Usage:
        log_safely(logger, logging.INFO, "Encounter created: %s by user %s", encounter_id, user_id)
        log_safely(logger, logging.ERROR, "Error occurred", exc_info=True)
        log_safely(logger, logging.INFO, "Processing", encounter_id=uuid_obj, user_id=uuid_obj)
    """
    # Extract exc_info if present (for exception logging)
    exc_info = kwargs.pop("exc_info", False)
    
    # Redact any PHI and UUIDs in the message text itself
    safe_message = redact_phi(message)
    
    # Process args - scrub UUIDs from string representations
    safe_args = []
    for arg in args:
        if isinstance(arg, (UUID,)):
            # UUID objects in args - scrub them (only approved fields in kwargs are allowed)
            safe_args.append("[REDACTED-UUID]")
        elif isinstance(arg, str):
            safe_args.append(redact_phi(arg))
        else:
            safe_args.append(arg)
    safe_args = tuple(safe_args)
    
    # Process kwargs - separate approved UUID fields from others
    approved_fields = {}
    other_kwargs = {}
    
    for key, value in kwargs.items():
        key_lower = key.lower()
        
        # Remove PHI fields completely - don't include them in logs
        if any(phi_field.lower() in key_lower for phi_field in PHI_FIELDS):
            continue
        
        # Check if this is an approved UUID field
        is_approved_uuid_field = any(approved_field.lower() in key_lower 
                                     for approved_field in APPROVED_UUID_FIELDS)
        
        if is_approved_uuid_field:
            # Approved UUID field - preserve UUIDs
            if isinstance(value, (UUID,)):
                approved_fields[key] = str(value)
            elif isinstance(value, str):
                # Check if it's a UUID string
                try:
                    UUID(value)
                    approved_fields[key] = value  # Valid UUID string - preserve
                except ValueError:
                    approved_fields[key] = redact_phi(value)  # Not a UUID - scrub it
            else:
                approved_fields[key] = str(value)
        else:
            # Not an approved field - scrub UUIDs
            if isinstance(value, str):
                other_kwargs[key] = redact_phi(value)
            elif isinstance(value, dict):
                other_kwargs[key] = redact_dict(value)
            elif isinstance(value, (UUID,)):
                other_kwargs[key] = "[REDACTED-UUID]"
            else:
                other_kwargs[key] = redact_phi(str(value))
    
    # Build the log message with approved fields appended
    if approved_fields:
        approved_str = ", ".join(f"{k}={v}" for k, v in approved_fields.items())
        safe_message = f"{safe_message} ({approved_str})"
    
    # Add exc_info back if it was present
    if exc_info:
        other_kwargs["exc_info"] = exc_info
    
    # Log with only standard logging kwargs (exc_info, extra, etc.)
    # Note: Python's logging doesn't accept arbitrary kwargs, so we include approved fields in message
    logger.log(level, safe_message, *safe_args, **other_kwargs)
