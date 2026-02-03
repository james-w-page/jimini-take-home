# Quick Start Guide

## Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

## Installation

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv sync
```

3. Set up environment variables:
```bash
# Copy the example .env file (if you created one) or set these manually:
export SECRET_KEY="your-secret-key-here"
export ALGORITHM="HS256"
export ACCESS_TOKEN_EXPIRE_MINUTES=30
```

To generate a secure secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Running the Application

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Authentication

### Get a JWT Token

Use HTTP Basic Authentication to get a JWT token:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -u admin:admin \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### Use the Token

Include the token in subsequent requests:

```bash
curl -X GET "http://localhost:8000/api/v1/encounters/enc_123" \
  -H "Authorization: Bearer <your-token>"
```

## Example API Calls

### Create an Encounter

```bash
curl -X POST "http://localhost:8000/api/v1/encounters" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "pat_123",
    "provider_id": "prov_456",
    "encounter_date": "2024-01-15T10:30:00Z",
    "encounter_type": "initial_assessment",
    "clinical_data": {
      "chief_complaint": "Anxiety and stress",
      "mental_status": "Alert and oriented",
      "assessment": "Generalized anxiety disorder"
    }
  }'
```

### Get an Encounter

```bash
curl -X GET "http://localhost:8000/api/v1/encounters/enc_123456" \
  -H "Authorization: Bearer <your-token>"
```

With filters:
```bash
curl -X GET "http://localhost:8000/api/v1/encounters/enc_123456?patient_id=pat_123&start_date=2024-01-01T00:00:00Z" \
  -H "Authorization: Bearer <your-token>"
```

### Get Audit Trail

```bash
curl -X GET "http://localhost:8000/api/v1/audit/encounters" \
  -H "Authorization: Bearer <your-token>"
```

With date range:
```bash
curl -X GET "http://localhost:8000/api/v1/audit/encounters?start_date=2024-01-01T00:00:00Z&end_date=2024-01-31T23:59:59Z" \
  -H "Authorization: Bearer <your-token>"
```

## Testing

Run tests:
```bash
uv run pytest
```

## Default Users

For development, the following users are configured:
- Username: `admin`, Password: `admin`
- Username: `provider1`, Password: `admin`

**Note**: In production, these should be replaced with proper user management and secure password storage.

## Architecture Notes

### In-Memory Storage

The current implementation uses in-memory storage (dictionaries) for simplicity. This is easily replaceable with a database:

1. Create a new storage class implementing the same interface
2. Replace `app.storage.in_memory.storage` with your database-backed storage
3. The API layer remains unchanged

### PHI Redaction

All logs and error messages are automatically sanitized to remove PHI:
- Patient IDs
- Email addresses
- Phone numbers
- SSN patterns
- Other known PHI fields

### Audit Trail

Every access to encounter data is automatically logged:
- Who accessed the data (user_id)
- When (timestamp)
- What (resource_id, event_type)
- Where (IP address, user agent)
