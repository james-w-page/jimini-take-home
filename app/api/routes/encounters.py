"""Encounter API routes"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends, Request, Query
from app.api.deps import get_current_user, get_client_ip
from app.models.encounter import Encounter, EncounterCreate, EncounterFilter, EncounterType
from app.storage.in_memory import storage
from app.core.phi_redaction import sanitize_error_message, log_safely
import logging

router = APIRouter(prefix="/encounters", tags=["encounters"])
logger = logging.getLogger(__name__)


@router.post("", response_model=Encounter, status_code=status.HTTP_201_CREATED)
async def create_encounter(
    encounter_data: EncounterCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new encounter record.
    
    Validates the request body and creates a new encounter with generated ID.
    Automatically logs an audit event for compliance.
    """
    try:
        user_id = current_user["user_id"]
        
        # Create encounter
        encounter = storage.create_encounter(encounter_data, created_by=user_id)
        
        # Log audit event
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        storage.create_audit_event(
            event_type="encounter_created",
            resource_type="encounter",
            resource_id=encounter.encounter_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={"encounter_type": encounter.encounter_type.value},
        )
        
        # Log safely (PHI redacted)
        log_safely(
            logger,
            logging.INFO,
            "Encounter created: %s by user %s",
            encounter.encounter_id,
            user_id,
        )
        
        return encounter
    
    except ValueError as e:
        # Validation error from Pydantic
        error_msg = f"Validation error: {str(e)}"
        safe_msg = sanitize_error_message(error_msg)
        log_safely(logger, logging.WARNING, "Validation error creating encounter: %s", safe_msg)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=safe_msg,
        )
    except Exception as e:
        # Unexpected error - don't leak internal details
        error_msg = "An error occurred while creating the encounter"
        safe_msg = sanitize_error_message(error_msg, {"error_type": type(e).__name__})
        log_safely(logger, logging.ERROR, "Error creating encounter: %s", safe_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_msg,
        )


@router.get("/{encounter_id}", response_model=Encounter)
async def get_encounter(
    encounter_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    encounter_type: Optional[EncounterType] = Query(None, description="Filter by encounter type"),
    start_date: Optional[datetime] = Query(None, description="Start of date range (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End of date range (ISO format)"),
):
    """
    Retrieve a specific encounter by ID.
    
    Supports optional query parameters for filtering:
    - patient_id: Filter by patient ID
    - provider_id: Filter by provider ID
    - encounter_type: Filter by encounter type
    - start_date: Start of date range (ISO format)
    - end_date: End of date range (ISO format)
    
    Automatically logs an audit event for compliance.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get encounter
        encounter = storage.get_encounter(encounter_id)
        
        if encounter is None:
            error_msg = f"Encounter not found: {encounter_id}"
            safe_msg = sanitize_error_message(error_msg)
            log_safely(logger, logging.WARNING, "Encounter not found: %s", encounter_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=safe_msg,
            )
        
        # Apply filters if provided
        filters = EncounterFilter(
            patient_id=patient_id,
            provider_id=provider_id,
            encounter_type=encounter_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        # If filters are provided, check if this encounter matches
        if any([patient_id, provider_id, encounter_type, start_date, end_date]):
            matching = storage.list_encounters(filters)
            if encounter not in matching:
                error_msg = "Encounter does not match filter criteria"
                safe_msg = sanitize_error_message(error_msg)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=safe_msg,
                )
        
        # Log audit event
        ip_address = get_client_ip(request)
        user_agent = request.headers.get("User-Agent")
        storage.create_audit_event(
            event_type="encounter_accessed",
            resource_type="encounter",
            resource_id=encounter_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={
                "filters_applied": {
                    "patient_id": patient_id is not None,
                    "provider_id": provider_id is not None,
                    "encounter_type": encounter_type is not None,
                    "date_range": start_date is not None or end_date is not None,
                }
            },
        )
        
        # Log safely (PHI redacted)
        log_safely(
            logger,
            logging.INFO,
            "Encounter accessed: %s by user %s",
            encounter_id,
            user_id,
        )
        
        return encounter
    
    except HTTPException:
        raise
    except ValueError as e:
        # Validation error (e.g., invalid date format)
        error_msg = f"Invalid filter parameter: {str(e)}"
        safe_msg = sanitize_error_message(error_msg)
        log_safely(logger, logging.WARNING, "Invalid filter parameter: %s", safe_msg)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=safe_msg,
        )
    except Exception as e:
        # Unexpected error
        error_msg = "An error occurred while retrieving the encounter"
        safe_msg = sanitize_error_message(error_msg, {"error_type": type(e).__name__})
        log_safely(logger, logging.ERROR, "Error retrieving encounter: %s", safe_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_msg,
        )
