"""Unit tests for API endpoints"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import UUID
from fastapi.testclient import TestClient
from app.main import app
from app.core.constants import get_patient_ids, get_provider_ids
from app.models.encounter import EncounterType
from app.storage.in_memory import storage


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    """Get admin authentication token"""
    response = client.post(
        "/api/v1/login",
        auth=("admin", "admin"),
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def user_token(client):
    """Get regular user authentication token"""
    response = client.post(
        "/api/v1/login",
        auth=("provider1", "admin"),
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def sample_encounter_data():
    """Sample encounter data for testing"""
    return {
        "patient_id": get_patient_ids()[0],
        "provider_id": get_provider_ids()[0],
        "encounter_date": datetime.now(timezone.utc).isoformat(),
        "encounter_type": EncounterType.INITIAL_ASSESSMENT.value,
        "clinical_data": {
            "chief_complaint": "Anxiety and stress",
            "mental_status": "Alert and oriented",
            "assessment": "Generalized anxiety disorder",
        },
    }


@pytest.fixture(autouse=True)
def clear_storage():
    """Clear storage before each test"""
    storage.clear()
    yield
    storage.clear()


class TestAuthentication:
    """Tests for authentication endpoints"""

    def test_login_success(self, client):
        """Test successful login"""
        response = client.post("/api/v1/login", auth=("admin", "admin"))
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post("/api/v1/login", auth=("admin", "wrongpassword"))
        assert response.status_code == 401

    def test_login_missing_auth(self, client):
        """Test login without authentication"""
        response = client.post("/api/v1/login")
        assert response.status_code == 401


class TestEncounters:
    """Tests for encounter endpoints"""

    def test_create_encounter_success(self, client, admin_token, sample_encounter_data):
        """Test successful encounter creation"""
        response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert "encounter_id" in data
        assert data["patient_id"] == sample_encounter_data["patient_id"]
        assert data["provider_id"] == sample_encounter_data["provider_id"]
        assert data["encounter_type"] == sample_encounter_data["encounter_type"]
        assert isinstance(UUID(data["encounter_id"]), UUID)

    def test_create_encounter_requires_auth(self, client, sample_encounter_data):
        """Test that encounter creation requires authentication"""
        response = client.post(
            "/api/v1/encounters",
            json=sample_encounter_data,
        )
        assert response.status_code == 401  # Unauthorized when no token provided

    def test_create_encounter_invalid_patient_id(self, client, admin_token, sample_encounter_data):
        """Test encounter creation with invalid patient ID"""
        invalid_data = sample_encounter_data.copy()
        invalid_data["patient_id"] = "550e8400-e29b-41d4-a716-446655449999"  # Not in known list
        
        response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=invalid_data,
        )
        assert response.status_code == 400
        assert "patient_id" in response.json()["detail"].lower()

    def test_create_encounter_invalid_provider_id(self, client, admin_token, sample_encounter_data):
        """Test encounter creation with invalid provider ID"""
        invalid_data = sample_encounter_data.copy()
        invalid_data["provider_id"] = "750e8400-e29b-41d4-a716-446655449999"  # Not in known list
        
        response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=invalid_data,
        )
        assert response.status_code == 400
        assert "provider_id" in response.json()["detail"].lower()

    def test_create_encounter_invalid_uuid_format(self, client, admin_token, sample_encounter_data):
        """Test encounter creation with invalid UUID format"""
        invalid_data = sample_encounter_data.copy()
        invalid_data["patient_id"] = "not-a-uuid"
        
        response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=invalid_data,
        )
        assert response.status_code == 422
        assert "uuid" in response.json()["detail"][0]["msg"].lower()

    def test_create_encounter_invalid_encounter_type(self, client, admin_token, sample_encounter_data):
        """Test encounter creation with invalid encounter type"""
        invalid_data = sample_encounter_data.copy()
        invalid_data["encounter_type"] = "BAD_TYPE"
        
        response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=invalid_data,
        )
        assert response.status_code == 422

    def test_get_encounter_success(self, client, admin_token, sample_encounter_data):
        """Test successful encounter retrieval"""
        # Create an encounter first
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        assert create_response.status_code == 201
        encounter_id = create_response.json()["encounter_id"]
        
        # Retrieve it
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["encounter_id"] == encounter_id
        assert data["patient_id"] == sample_encounter_data["patient_id"]

    def test_get_encounter_not_found(self, client, admin_token):
        """Test retrieving non-existent encounter"""
        fake_id = "550e8400-e29b-41d4-a716-446655449999"
        response = client.get(
            f"/api/v1/encounters/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404

    def test_get_encounter_requires_auth(self, client):
        """Test that encounter retrieval requires authentication"""
        fake_id = "550e8400-e29b-41d4-a716-446655449999"
        response = client.get(f"/api/v1/encounters/{fake_id}")
        assert response.status_code == 401  # Unauthorized when no token provided

    def test_get_encounter_with_patient_filter(self, client, admin_token, sample_encounter_data):
        """Test encounter retrieval with patient_id filter"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Retrieve with matching filter
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"patient_id": sample_encounter_data["patient_id"]},
        )
        assert response.status_code == 200
        
        # Retrieve with non-matching filter
        other_patient = get_patient_ids()[1]
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"patient_id": other_patient},
        )
        assert response.status_code == 404

    def test_get_encounter_with_encounter_type_filter(self, client, admin_token, sample_encounter_data):
        """Test encounter retrieval with encounter_type filter"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Retrieve with matching filter
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"encounter_type": sample_encounter_data["encounter_type"]},
        )
        assert response.status_code == 200
        
        # Retrieve with non-matching filter
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"encounter_type": EncounterType.FOLLOW_UP.value},
        )
        assert response.status_code == 404

    def test_get_encounter_with_date_range_filter(self, client, admin_token, sample_encounter_data):
        """Test encounter retrieval with date range filter"""
        # Create an encounter with specific date
        encounter_date = datetime.now(timezone.utc)
        encounter_data = sample_encounter_data.copy()
        encounter_data["encounter_date"] = encounter_date.isoformat()
        
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Retrieve with matching date range
        start_date = (encounter_date - timedelta(days=1)).isoformat()
        end_date = (encounter_date + timedelta(days=1)).isoformat()
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"start_date": start_date, "end_date": end_date},
        )
        assert response.status_code == 200
        
        # Retrieve with non-matching date range
        future_start = (encounter_date + timedelta(days=10)).isoformat()
        future_end = (encounter_date + timedelta(days=20)).isoformat()
        response = client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"start_date": future_start, "end_date": future_end},
        )
        assert response.status_code == 404


class TestAudit:
    """Tests for audit endpoints"""

    def test_get_audit_trail_requires_admin(self, client, admin_token, user_token):
        """Test that audit trail requires admin access"""
        # Admin can access
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        
        # Regular user cannot access
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()

    def test_get_audit_trail_requires_auth(self, client):
        """Test that audit trail requires authentication"""
        response = client.get("/api/v1/audit/encounters")
        assert response.status_code == 401  # Unauthorized when no token provided

    def test_get_audit_trail_after_encounter_creation(self, client, admin_token, sample_encounter_data):
        """Test that audit trail captures encounter creation"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Get audit trail
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        
        # Find the creation event
        creation_events = [e for e in events if e["event_type"] == "encounter_created"]
        assert len(creation_events) >= 1
        assert creation_events[0]["resource_id"] == encounter_id

    def test_get_audit_trail_with_resource_id_filter(self, client, admin_token, sample_encounter_data):
        """Test audit trail filtering by resource_id"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Access the encounter (creates another audit event)
        client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        # Get audit trail filtered by resource_id
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"resource_id": encounter_id},
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 2  # creation + access
        assert all(e["resource_id"] == encounter_id for e in events)

    def test_get_audit_trail_with_user_id_filter(self, client, admin_token, sample_encounter_data):
        """Test audit trail filtering by user_id"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Get admin user_id from token (we know it's the admin UUID)
        admin_user_id = "850e8400-e29b-41d4-a716-446655440000"
        
        # Get audit trail filtered by user_id
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"user_id": admin_user_id},
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert all(str(e["user_id"]) == admin_user_id for e in events)

    def test_get_audit_trail_with_event_type_filter(self, client, admin_token, sample_encounter_data):
        """Test audit trail filtering by event_type"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Access the encounter
        client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        # Get audit trail filtered by event_type
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"event_type": "encounter_created"},
        )
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert all(e["event_type"] == "encounter_created" for e in events)

    def test_get_audit_trail_with_date_range(self, client, admin_token, sample_encounter_data):
        """Test audit trail filtering by date range"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        
        # Get audit trail with date range
        start_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        end_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        
        response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"start_date": start_date, "end_date": end_date},
        )
        assert response.status_code == 200
        events = response.json()
        # Should have at least the creation event
        assert len(events) >= 1


class TestAuditTrailCreation:
    """Tests that audit trails are created for encounter operations"""

    def test_audit_trail_created_on_encounter_creation(self, client, admin_token, sample_encounter_data):
        """Test that creating an encounter creates an audit event"""
        # Get initial audit count
        initial_response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        initial_count = len(initial_response.json())
        
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        assert create_response.status_code == 201
        encounter_id = create_response.json()["encounter_id"]
        
        # Check audit trail
        audit_response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        events = audit_response.json()
        assert len(events) == initial_count + 1
        
        # Verify the event
        creation_events = [e for e in events if e["event_type"] == "encounter_created" and e["resource_id"] == encounter_id]
        assert len(creation_events) == 1
        event = creation_events[0]
        assert event["resource_type"] == "encounter"
        assert isinstance(UUID(event["event_id"]), UUID)
        assert isinstance(UUID(event["user_id"]), UUID)

    def test_audit_trail_created_on_encounter_access(self, client, admin_token, sample_encounter_data):
        """Test that accessing an encounter creates an audit event"""
        # Create an encounter
        create_response = client.post(
            "/api/v1/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=sample_encounter_data,
        )
        encounter_id = create_response.json()["encounter_id"]
        
        # Get initial audit count
        initial_response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        initial_count = len(initial_response.json())
        
        # Access the encounter
        client.get(
            f"/api/v1/encounters/{encounter_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        
        # Check audit trail
        audit_response = client.get(
            "/api/v1/audit/encounters",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        events = audit_response.json()
        assert len(events) == initial_count + 1
        
        # Verify the access event
        access_events = [e for e in events if e["event_type"] == "encounter_accessed" and e["resource_id"] == encounter_id]
        assert len(access_events) == 1
        event = access_events[0]
        assert event["resource_type"] == "encounter"
        assert "ip_address" in event or event["ip_address"] is None
        assert "user_agent" in event or event["user_agent"] is None
