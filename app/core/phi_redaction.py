"""PHI (Protected Health Information) redaction utilities for logs and error messages"""

import re
import logging
from typing import Any, Dict, List, Union
from functools import wraps


# Patterns that might indicate PHI
PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN format XXX-XX-XXXX
    r"\b\d{3}\.\d{2}\.\d{4}\b",  # SSN format XXX.XX.XXXX
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email addresses
    r"\b\d{3}-\d{3}-\d{4}\b",  # Phone numbers XXX-XXX-XXXX
    r"\b\(\d{3}\)\s?\d{3}-\d{4}\b",  # Phone numbers (XXX) XXX-XXXX
    r"\b\d{10}\b",  # 10-digit numbers (could be phone or ID)
]

# Fields that are known to contain PHI
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


class PHIRedactingFormatter(logging.Formatter):
    """Custom logging formatter that redacts PHI from log messages"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record and redact PHI"""
        original_msg = super().format(record)
        return redact_phi(original_msg)


def redact_phi(text: str) -> str:
    """
    Redact PHI from text string.
    
    Replaces potential PHI with [REDACTED] markers.
    """
    if not isinstance(text, str):
        text = str(text)

    # Redact patterns
    redacted = text
    for pattern in PHI_PATTERNS:
        redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    return redacted


def redact_dict(data: Dict[str, Any], fields_to_redact: set = None) -> Dict[str, Any]:
    """
    Redact PHI from dictionary, replacing values of known PHI fields.
    
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
        
        if is_phi_field and value is not None:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, fields_to_redact)
        elif isinstance(value, list):
            redacted[key] = [redact_dict(item, fields_to_redact) if isinstance(item, dict) else 
                           ("[REDACTED]" if is_phi_field else item) for item in value]
        else:
            redacted[key] = value
    
    return redacted


def sanitize_error_message(error_msg: str, context: Dict[str, Any] = None) -> str:
    """
    Sanitize error messages to remove PHI.
    
    Args:
        error_msg: Original error message
        context: Optional context dictionary that might contain PHI
    
    Returns:
        Sanitized error message safe for logging
    """
    # Redact patterns in the message itself
    sanitized = redact_phi(error_msg)
    
    # If context provided, check for PHI fields
    if context:
        context_str = str(redact_dict(context))
        # Don't include full context in error message, just note if PHI was present
        if any(field in str(context).lower() for field in PHI_FIELDS):
            sanitized += " [Context contains PHI - redacted]"
    
    return sanitized


def log_safely(logger: logging.Logger, level: int, message: str, *args, **kwargs):
    """
    Safely log a message with PHI redaction.
    
    Usage:
        log_safely(logger, logging.INFO, "Processing patient %s", patient_id)
        log_safely(logger, logging.ERROR, "Error occurred", exc_info=True)
    """
    # Extract exc_info if present (for exception logging)
    exc_info = kwargs.pop("exc_info", False)
    
    # Redact any PHI in the message and args
    safe_message = redact_phi(message)
    safe_args = tuple(redact_phi(str(arg)) if isinstance(arg, str) else arg for arg in args)
    
    # Redact kwargs
    safe_kwargs = {}
    for key, value in kwargs.items():
        if key.lower() in [f.lower() for f in PHI_FIELDS]:
            safe_kwargs[key] = "[REDACTED]"
        elif isinstance(value, str):
            safe_kwargs[key] = redact_phi(value)
        elif isinstance(value, dict):
            safe_kwargs[key] = redact_dict(value)
        else:
            safe_kwargs[key] = value
    
    # Add exc_info back if it was present
    if exc_info:
        safe_kwargs["exc_info"] = exc_info
    
    logger.log(level, safe_message, *safe_args, **safe_kwargs)
