# Architecture and Design Decisions

## Overview

This HIPAA-Compliant Patient Encounter API is built with a focus on security, compliance, and clean architecture. The design emphasizes separation of concerns, testability, and extensibility.

## Technology Stack

- **FastAPI**: Modern, fast Python web framework with automatic API documentation
- **Pydantic v2**: Data validation and settings management
- **Python-JOSE**: JWT token handling
- **Passlib**: Secure password hashing (bcrypt)
- **uv**: Fast Python package manager

## Architecture Layers

### 1. API Layer (`app/api/`)
- **Routes**: HTTP endpoint handlers
- **Dependencies**: Authentication, request parsing, IP extraction
- **Error Handling**: Consistent error responses with PHI redaction

### 2. Business Logic Layer (`app/models/`)
- **Pydantic Models**: Data validation and serialization
- **Enums**: Type-safe constants (EncounterType)
- **Validation**: Field-level validation with clear error messages

### 3. Storage Layer (`app/storage/`)
- **In-Memory Storage**: Dictionary-based storage with indexes
- **Interface**: Easy to replace with database (SQLAlchemy, etc.)
- **Indexes**: O(1) lookups by ID, efficient filtering

### 4. Core Layer (`app/core/`)
- **Configuration**: Environment-based settings
- **Security**: JWT creation/validation, password hashing
- **PHI Redaction**: Log sanitization utilities

## Design Decisions

### 1. Separation of Concerns

**Decision**: Clear boundaries between API, business logic, and data access.

**Implementation**:
- API routes handle HTTP concerns only
- Business logic in Pydantic models
- Storage layer abstracts data persistence
- Core utilities are reusable across layers

**Benefits**:
- Easy to test each layer independently
- Simple to swap storage implementations
- Clear responsibilities

### 2. Validation Strategy

**Decision**: Validate at API boundaries using Pydantic.

**Implementation**:
- Request models (`EncounterCreate`) validate input
- Response models (`Encounter`) ensure output consistency
- Field validators for business rules (e.g., date ranges)
- Custom error messages without exposing internals

**Benefits**:
- Automatic validation documentation
- Type safety
- Clear error messages for API consumers

### 3. Error Handling

**Decision**: Consistent error handling that never leaks PHI or internal details.

**Implementation**:
- Custom exception handlers in `main.py`
- PHI redaction in all error messages
- Generic messages for unexpected errors
- Structured error responses

**Benefits**:
- HIPAA compliance (no PHI in logs/errors)
- Security (no information leakage)
- Better debugging (errors logged internally)

### 4. PHI Redaction

**Decision**: Multi-layer PHI redaction strategy.

**Implementation**:
- Pattern-based redaction (SSN, email, phone)
- Field-based redaction (known PHI fields)
- Custom logging formatter
- Error message sanitization

**Benefits**:
- Comprehensive protection
- Automatic application
- Easy to extend with new patterns

### 5. Audit Trail

**Decision**: Automatic audit logging for all data access.

**Implementation**:
- Audit events created on every encounter access
- Stored in same storage layer (easily moved to separate system)
- Includes user, timestamp, IP, user agent
- Queryable by date range, user, resource

**Benefits**:
- HIPAA compliance requirement
- Security monitoring
- Forensics capability

### 6. Authentication

**Decision**: JWT-based authentication with HTTP Basic for token acquisition.

**Implementation**:
- HTTP Basic Auth for login (simple, standard)
- JWT tokens for API access
- Token validation in dependency injection
- Mock user database (easily replaceable)

**Benefits**:
- Stateless authentication
- Standard approach
- Easy to integrate with identity providers

### 7. In-Memory Storage

**Decision**: Use dictionaries/lists for storage, mimicking SQL interface.

**Implementation**:
- Primary storage: `Dict[str, Encounter]` for O(1) lookups
- Indexes: Separate dicts for patient/provider lookups
- Filtering: List comprehensions with multiple criteria
- Easy to replace with SQLAlchemy or similar

**Benefits**:
- No external dependencies
- Fast for development/testing
- Clear interface for database migration
- SQL-like query patterns

**Migration Path**:
```python
# Replace app/storage/in_memory.py with:
from sqlalchemy.orm import Session

class DatabaseStorage:
    def __init__(self, db: Session):
        self.db = db
    
    def get_encounter(self, encounter_id: str):
        return self.db.query(Encounter).filter(...).first()
    # ... same interface
```

## Extensibility

### Adding New Encounter Types

1. Add to `EncounterType` enum in `app/models/encounter.py`
2. No other changes needed (handled by enum validation)

### Adding New Fields

1. Add field to `EncounterBase` model
2. Add validation if needed
3. Storage layer automatically handles it (dict-based)

### Adding New Endpoints

1. Create route in `app/api/routes/`
2. Use existing dependencies (`get_current_user`, etc.)
3. Follow error handling patterns
4. Add audit logging if accessing PHI

### Replacing Storage

1. Implement same interface as `InMemoryStorage`
2. Replace `storage` instance in routes
3. All business logic remains unchanged

## Testing Strategy

### Unit Tests
- PHI redaction utilities
- Storage layer operations
- Model validation

### Integration Tests
- API endpoints with authentication
- Error handling
- Audit trail creation

### Testability Features
- Dependency injection for storage
- Mockable authentication
- Isolated components

## Security Considerations

1. **PHI Protection**: Never logged or exposed in errors
2. **Input Validation**: All inputs validated at boundaries
3. **Authentication**: Required for all endpoints
4. **Audit Trail**: Complete access logging
5. **Error Messages**: Generic, no information leakage
6. **Password Hashing**: bcrypt with proper salt rounds

## Performance Considerations

- In-memory storage: O(1) lookups, O(n) filtering
- Indexes for common queries (patient, provider)
- JWT validation: O(1) with caching
- No database overhead (for current implementation)

## Future Enhancements

1. **Database Integration**: Replace in-memory with PostgreSQL
2. **Caching**: Add Redis for token validation
3. **Rate Limiting**: Protect against abuse
4. **Encryption**: Encrypt PHI at rest
5. **Role-Based Access**: Fine-grained permissions
6. **API Versioning**: Support multiple API versions
7. **Webhooks**: Notify external systems of events
