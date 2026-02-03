# HIPAA-Compliant Patient Encounter API

A REST API service for managing patient encounter records with HIPAA compliance features including PHI redaction, audit trails, and secure authentication.

## Features

- **HIPAA Compliance**: PHI redaction in logs, audit trails, secure authentication
- **FastAPI**: Modern, fast Python web framework
- **JWT Authentication**: Secure token-based authentication
- **Pydantic Validation**: Strong type checking and validation
- **In-Memory Storage**: Simple hashmap-based storage (easily replaceable with database)

## Technology Stack

- FastAPI
- Pydantic v2
- Python-JOSE (JWT)
- Passlib (password hashing)
- uv (package management)

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration settings
│   │   ├── security.py      # JWT and authentication
│   │   └── phi_redaction.py # PHI redaction utilities
│   ├── models/
│   │   ├── __init__.py
│   │   ├── encounter.py     # Encounter data models
│   │   └── audit.py         # Audit trail models
│   ├── storage/
│   │   ├── __init__.py
│   │   └── in_memory.py     # In-memory storage implementation
│   └── api/
│       ├── __init__.py
│       ├── deps.py          # API dependencies (auth, etc.)
│       └── routes/
│           ├── __init__.py
│           ├── encounters.py
│           └── audit.py
└── tests/
    └── ...
```

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
cp .env.example .env
# Edit .env and set SECRET_KEY and other values
```

## Running the Application

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication

First, obtain a JWT token:

```bash
POST /api/v1/auth/login
{
  "username": "admin",
  "password": "admin"
}
```

Use the token in subsequent requests:
```
Authorization: Bearer <token>
```

### Encounters

- `POST /api/v1/encounters` - Create a new encounter
- `GET /api/v1/encounters/{encounter_id}` - Get a specific encounter
- `GET /api/v1/audit/encounters` - Get audit trail for encounters

## Development

Run tests:
```bash
uv run pytest
```

Format code:
```bash
uv run black app tests
uv run ruff check app tests
```

## Security Features

1. **PHI Redaction**: All logs and error messages are sanitized to remove PHI
2. **JWT Authentication**: Secure token-based authentication
3. **Input Validation**: Comprehensive Pydantic validation at API boundaries
4. **Audit Trail**: Complete tracking of who accessed what data and when

## License

MIT
