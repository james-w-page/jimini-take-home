"""In-memory storage implementation using dictionaries"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from app.models.encounter import Encounter, EncounterCreate, EncounterFilter
from app.models.audit import AuditEvent, AuditFilter


class InMemoryStorage:
    """
    In-memory storage implementation using dictionaries.
    
    This provides a simple SQL-like interface that can be easily replaced
    with a real database. Uses hash maps for O(1) lookups by ID and lists
    for sequential access and filtering.
    """

    def __init__(self):
        """Initialize storage with empty dictionaries"""
        # Primary storage: encounter_id -> Encounter
        self._encounters: Dict[UUID, Encounter] = {}
        
        # Indexes for faster lookups
        self._encounters_by_patient: Dict[UUID, List[UUID]] = {}  # patient_id -> [encounter_ids]
        self._encounters_by_provider: Dict[UUID, List[UUID]] = {}  # provider_id -> [encounter_ids]
        
        # Audit trail storage
        self._audit_events: Dict[str, AuditEvent] = {}
        self._audit_by_resource: Dict[str, List[str]] = {}  # resource_id -> [event_ids]

    def create_encounter(
        self, encounter_data: EncounterCreate, created_by: str
    ) -> Encounter:
        """
        Create a new encounter record.
        
        Args:
            encounter_data: Encounter data to create
            created_by: User ID who created the record
        
        Returns:
            Created Encounter with generated ID
        """
        encounter_id = uuid.uuid4()
        now = datetime.utcnow()
        
        encounter = Encounter(
            encounter_id=encounter_id,
            **encounter_data.model_dump(),
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )
        
        # Store in primary storage
        self._encounters[encounter_id] = encounter
        
        # Update indexes
        patient_id = encounter.patient_id
        provider_id = encounter.provider_id
        
        if patient_id not in self._encounters_by_patient:
            self._encounters_by_patient[patient_id] = []
        self._encounters_by_patient[patient_id].append(encounter_id)
        
        if provider_id not in self._encounters_by_provider:
            self._encounters_by_provider[provider_id] = []
        self._encounters_by_provider[provider_id].append(encounter_id)
        
        return encounter

    def get_encounter(self, encounter_id: UUID) -> Optional[Encounter]:
        """
        Get an encounter by ID.
        
        Args:
            encounter_id: Encounter identifier
        
        Returns:
            Encounter if found, None otherwise
        """
        return self._encounters.get(encounter_id)

    def list_encounters(self, filters: Optional[EncounterFilter] = None) -> List[Encounter]:
        """
        List encounters with optional filtering.
        
        Args:
            filters: Optional filter criteria
        
        Returns:
            List of matching encounters
        """
        if filters is None:
            return list(self._encounters.values())
        
        # Start with all encounters
        candidates = list(self._encounters.values())
        
        # Apply filters
        if filters.patient_id:
            patient_encounter_ids = self._encounters_by_patient.get(filters.patient_id, [])
            candidates = [e for e in candidates if e.encounter_id in patient_encounter_ids]
        
        if filters.provider_id:
            provider_encounter_ids = self._encounters_by_provider.get(filters.provider_id, [])
            candidates = [e for e in candidates if e.encounter_id in provider_encounter_ids]
        
        if filters.encounter_type:
            candidates = [e for e in candidates if e.encounter_type == filters.encounter_type]
        
        if filters.start_date:
            candidates = [e for e in candidates if e.encounter_date >= filters.start_date]
        
        if filters.end_date:
            candidates = [e for e in candidates if e.encounter_date <= filters.end_date]
        
        return candidates

    def create_audit_event(
        self,
        event_type: str,
        resource_type: str,
        resource_id: str | UUID,
        user_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[dict] = None,
    ) -> AuditEvent:
        """
        Create an audit trail event.
        
        Args:
            event_type: Type of event (e.g., 'encounter_created', 'encounter_accessed')
            resource_type: Type of resource (e.g., 'encounter')
            resource_id: ID of the resource
            user_id: User who performed the action
            ip_address: Optional IP address
            user_agent: Optional user agent
            additional_data: Optional additional context
        
        Returns:
            Created AuditEvent
        """
        event_id = f"audit_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow()
        
        # Convert resource_id to string if it's a UUID
        resource_id_str = str(resource_id) if isinstance(resource_id, UUID) else resource_id
        
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=resource_id_str,
            user_id=user_id,
            timestamp=now,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data=additional_data or {},
        )
        
        # Store in primary storage
        self._audit_events[event_id] = event
        
        # Update index (use string version for indexing)
        if resource_id_str not in self._audit_by_resource:
            self._audit_by_resource[resource_id_str] = []
        self._audit_by_resource[resource_id_str].append(event_id)
        
        return event

    def list_audit_events(self, filters: Optional[AuditFilter] = None) -> List[AuditEvent]:
        """
        List audit events with optional filtering.
        
        Args:
            filters: Optional filter criteria
        
        Returns:
            List of matching audit events
        """
        if filters is None:
            return list(self._audit_events.values())
        
        # Start with all events
        candidates = list(self._audit_events.values())
        
        # Apply filters
        if filters.resource_type:
            candidates = [e for e in candidates if e.resource_type == filters.resource_type]
        
        if filters.resource_id:
            resource_event_ids = self._audit_by_resource.get(filters.resource_id, [])
            candidates = [e for e in candidates if e.event_id in resource_event_ids]
        
        if filters.user_id:
            candidates = [e for e in candidates if e.user_id == filters.user_id]
        
        if filters.event_type:
            candidates = [e for e in candidates if e.event_type == filters.event_type]
        
        if filters.start_date:
            candidates = [e for e in candidates if e.timestamp >= filters.start_date]
        
        if filters.end_date:
            candidates = [e for e in candidates if e.timestamp <= filters.end_date]
        
        return candidates

    def clear(self):
        """Clear all data (useful for testing)"""
        self._encounters.clear()
        self._encounters_by_patient.clear()
        self._encounters_by_provider.clear()
        self._audit_events.clear()
        self._audit_by_resource.clear()


# Global storage instance
storage = InMemoryStorage()
