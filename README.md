# HIPAA-Compliant Patient Encounter API

A REST API service for managing patient encounter records with HIPAA compliance features including PHI redaction, audit trails, and secure authentication.

## Setup & Running

### Dependencies Installation

1. Install `uv` (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install project dependencies:
```bash
uv sync
```

3. Set up environment variables (optional):
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY and other values
```

### How to Run the Application

Start the development server:
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### How to Run Tests

**Unit Tests:**
```bash
uv run pytest
```

**Integration Tests:**
```bash
uv run ./scripts/test_api.py
```

**Run specific test files:**
```bash
uv run pytest tests/test_api.py -v          # API endpoint tests
uv run pytest tests/test_phi_redaction.py -v # PHI redaction tests
uv run pytest tests/test_storage.py -v      # Storage layer tests
```

## Design Decisions

### Key Architectural Choices and Why

**1. Layered Architecture with Clear Separation of Concerns**
- **API Layer** (`app/api/`): Handles HTTP concerns, authentication, and request/response formatting
- **Business Logic Layer** (`app/models/`): Pydantic models for validation and data contracts
- **Storage Layer** (`app/storage/`): Abstracted data persistence with a simple interface
- **Core Layer** (`app/core/`): Reusable utilities (security, PHI redaction, configuration)

**Why**: This separation makes the codebase testable, maintainable, and easy to extend. Each layer has a single responsibility, making it straightforward to swap implementations (e.g., replace in-memory storage with a database) without affecting other layers.

**2. Pydantic Validation at API Boundaries**
- All request/response data validated using Pydantic models
- Field-level validators for business rules (e.g., UUID format, known patient/provider IDs)
- Custom error messages that don't expose internal implementation details

**Why**: Provides automatic validation, type safety, and clear error messages for API consumers. Pydantic's integration with FastAPI automatically generates OpenAPI documentation.

**3. In-Memory Storage with SQL-like Interface**
- Filtering methods that mimic SQL WHERE clauses
- Simple interface that can be easily replaced with a database

**Why**: Eliminates external dependencies for development and testing, while providing a clear migration path to a persistent database. The interface design ensures business logic remains unchanged when switching storage backends.

**4. Multi-Layer PHI Redaction Strategy**
- Pattern-based redaction (SSN, email, phone regex patterns)
- Field-based redaction (removes known PHI fields from dictionaries)
- UUID scrubbing (removes UUIDs except for approved operational fields)
- Custom logging formatter that automatically sanitizes all log output
- Error message sanitization

**Why**: HIPAA compliance requires that PHI never appears in logs or error messages. Multiple layers ensure comprehensive protection even if one layer misses something.

**5. Automatic Audit Trail**
- Every encounter access creates an audit event
- Includes user ID, timestamp, IP address, user agent, and resource accessed
- Queryable by date range, user, resource ID, and event type

**Why**: HIPAA requires audit trails for compliance. Automatic logging ensures nothing is missed and provides security monitoring capabilities.

**6. JWT Authentication with Role-Based Access Control**
- HTTP Basic Auth for token acquisition (simple, standard)
- JWT tokens for stateless API authentication
- Role-based access control (ADMIN vs USER roles)
- Admin-only access to audit endpoints

**Why**: Stateless authentication scales well, and JWT is a standard approach that's easy to integrate with identity providers. Role-based access provides fine-grained security.

### Trade-offs Considered

**In-Memory Storage vs. Database**
- **Chosen**: In-memory storage for simplicity and zero dependencies
- **Trade-off**: Data is lost on restart, but this is acceptable for a take-home project
- **Migration**: The storage interface is designed to be easily replaced with SQLAlchemy or similar

**Custom PHI Redaction vs. Third-Party Library**
- **Chosen**: Custom implementation for full control and no external dependencies
- **Trade-off**: May miss some edge cases that a specialized library would catch
- **Future**: TODO added to consider [DataFog](https://github.com/DataFog/datafog-python) for enhanced PII detection

**Mock User Database vs. Real Authentication**
- **Chosen**: Hard-coded mock users for simplicity
- **Trade-off**: Not production-ready, but sufficient for demonstrating authentication patterns
- **Production**: Would integrate with OAuth2, LDAP, or a user management service

**Comprehensive Error Messages vs. Security**
- **Chosen**: Generic error messages that don't leak internal details or PHI
- **Trade-off**: Less helpful for debugging, but critical for HIPAA compliance
- **Solution**: Detailed errors logged internally (with PHI redaction), generic messages returned to clients

### What You'd Change for Production

1. **Persistent Database**: Replace in-memory storage with PostgreSQL or similar, using SQLAlchemy ORM. Would include the following tables:
   - **User table**: Store user accounts with authentication credentials and roles
   - **Provider table**: Store provider/clinician information
   - **Patient table**: Store patient information (PHI)
   - **Organization table**: Store organization information, with users belonging to organizations
2. **Real Authentication**: Integrate with OAuth2 provider, LDAP, or identity management service
3. **Enhanced PHI Detection**: Integrate [DataFog](https://github.com/DataFog/datafog-python) or similar library for more comprehensive PII detection
4. **Encryption at Rest**: Encrypt PHI fields in the database using field-level encryption
5. **Rate Limiting**: Add rate limiting to prevent abuse and DDoS attacks
6. **Caching**: Add Redis for JWT token validation caching and frequently accessed data
7. **Audit Trail Separation**: Move audit logs to a separate, append-only system (e.g., dedicated audit database or log aggregation service). Likely event driven (write to kafka/pubsub/redis)
8. **API Versioning**: Implement proper API versioning strategy for backward compatibility
9. **Monitoring & Alerting**: Add comprehensive logging, metrics (Prometheus), and alerting (e.g., for suspicious access patterns)


## Testing Philosophy

### What You Tested and Why

**1. Unit Tests for PHI Redaction (`tests/test_phi_redaction.py`)**
- **Why**: PHI redaction is critical for HIPAA compliance. Any failure could result in PHI leakage.
- **Coverage**: 
  - UUID scrubbing in messages and dictionaries
  - PHI field removal from nested structures
  - Approved UUID field preservation
  - Error message sanitization
  - Edge cases (empty dicts, None values, case sensitivity)

**2. Unit Tests for Storage Layer (`tests/test_storage.py`)**
- **Why**: Storage is a core component that must work correctly. Testing ensures data integrity.
- **Coverage**:
  - Encounter creation and retrieval
  - Filtering by various criteria
  - UUID handling and validation

**3. API Integration Tests (`tests/test_api.py`)**
- **Why**: End-to-end testing ensures the API works correctly with authentication, validation, and error handling.
- **Coverage**:
  - Authentication (success, failure, missing credentials)
  - Encounter creation (success, validation errors, invalid IDs)
  - Encounter retrieval (success, not found, filtering)
  - Audit trail access (admin-only, filtering, date ranges)
  - Role-based access control

**4. Integration Test Script (`scripts/test_api.py`)**
- **Why**: Manual integration testing script that exercises the full API workflow.
- **Coverage**:
  - Login and token acquisition
  - Creating multiple encounters
  - Querying encounters with filters
  - Querying audit trails
  - Validation error scenarios

### How to Run Tests

**All Tests:**
```bash
uv run pytest
```

**With Verbose Output:**
```bash
uv run pytest -v
```

**Specific Test Categories:**
```bash
uv run pytest tests/test_api.py -v          # API endpoint tests
uv run pytest tests/test_phi_redaction.py -v # PHI redaction tests
uv run pytest tests/test_storage.py -v      # Storage layer tests
```

**Integration Tests (requires running server):**
```bash
# In one terminal, start the server:
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, run integration tests:
uv run ./scripts/test_api.py
```

**Test Coverage:**
```bash
uv run pytest --cov=app --cov-report=html
```

### What You'd Add with More Time

1. **Performance Tests**: Load testing with tools like Locust or k6 to ensure the API handles expected traffic
2. **Security Tests**: 
   - Penetration testing for authentication bypass attempts
   - SQL injection tests (when database is added)
   - XSS and CSRF protection tests
3. **End-to-End Tests**: Full workflow tests that simulate real user scenarios
4. **PHI Redaction Edge Cases**: More comprehensive tests for unusual PHI formats and edge cases
5. **Database Migration Tests**: When moving to persistent storage, test migration scripts and rollback procedures

## API Endpoints

### Authentication

First, obtain a JWT token:
```bash
POST /api/v1/auth/login
Authorization: Basic <base64(username:password)>
```

Use the token in subsequent requests:
```
Authorization: Bearer <token>
```

### Encounters

- `POST /api/v1/encounters` - Create a new encounter
- `GET /api/v1/encounters/{encounter_id}` - Get a specific encounter (supports filtering via query params)
- `GET /api/v1/audit/encounters` - Get audit trail for encounters (admin only)

## Technology Stack

- **FastAPI**: Modern, fast Python web framework
- **Pydantic v2**: Data validation and settings management
- **Python-JOSE**: JWT token handling
- **bcrypt**: Secure password hashing
- **uv**: Fast Python package manager

## License

MIT
