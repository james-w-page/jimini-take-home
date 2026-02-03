"""Audit trail API routes"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, Depends, Query
from app.api.deps import get_current_user
from app.models.audit import AuditEvent, AuditFilter
from app.storage.in_memory import storage
from app.core.phi_redaction import sanitize_error_message, log_safely
import logging

router = APIRouter(prefix="/audit", tags=["audit"])
logger = logging.getLogger(__name__)


@router.get("/encounters", response_model=list[AuditEvent])
async def get_encounter_audit_trail(
    current_user: dict = Depends(get_current_user),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID (UUID)"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
):
    """
    Get audit trail for encounters.
    
    Returns audit events for encounter resources with optional filtering:
    - resource_id: Filter by specific encounter ID
    - user_id: Filter by user who performed the action
    - event_type: Filter by event type (e.g., 'encounter_created', 'encounter_accessed')
    - start_date: Start of date range (ISO format)
    - end_date: End of date range (ISO format)
    
    This endpoint tracks who accessed what data and when for HIPAA compliance.
    """
    try:
        # Build filter
        filters = AuditFilter(
            resource_type="encounter",
            resource_id=resource_id,
            user_id=user_id,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
        )
        
        # Get audit events
        events = storage.list_audit_events(filters)
        
        # Log access to audit trail (meta-audit)
        log_safely(
            logger,
            logging.INFO,
            "Audit trail accessed by user %s with filters: resource_id=%s, user_id=%s, event_type=%s",
            current_user["user_id"],
            resource_id or "None",
            user_id or "None",
            event_type or "None",
        )
        
        return events
    
    except ValueError as e:
        # Validation error (e.g., invalid date range)
        error_msg = f"Invalid filter parameter: {str(e)}"
        safe_msg = sanitize_error_message(error_msg)
        log_safely(logger, logging.WARNING, "Invalid audit filter parameter: %s", safe_msg)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=safe_msg,
        )
    except Exception as e:
        # Unexpected error
        error_msg = "An error occurred while retrieving the audit trail"
        safe_msg = sanitize_error_message(error_msg, {"error_type": type(e).__name__})
        log_safely(logger, logging.ERROR, "Error retrieving audit trail: %s", safe_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=safe_msg,
        )
