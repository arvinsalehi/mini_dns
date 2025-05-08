"""
NOTE Generated via Cursor running on claude-3.7-sonnet. Supervised by Arvin Salehi.

Tests for DNS API functionality.

This module contains comprehensive tests for the DNS API, covering:
1. CNAME record constraints
2. Record conflict prevention
3. CNAME chaining and circular reference detection
4. Duplicate record prevention
5. Input validation
6. Error handling and status codes
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
import mongomock
from unittest.mock import patch


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_collection():
    """Set up a mock MongoDB collection for testing."""
    with patch('app.db.connectors.get_dns_collection') as mock_get_collection:
        # Create mock collection
        collection = mongomock.MongoClient().db.collection
        mock_get_collection.return_value = collection
        
        # Clear collection before each test
        collection.delete_many({})
        
        yield collection
        
        # Clean up after test
        collection.delete_many({})


def test_add_a_record_success(client, mock_collection):
    """Test successfully adding an A record."""
    response = client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "example.com"
    assert data["type"] == "A"
    assert data["value"] == "192.168.1.1"


def test_add_cname_record_success(client, mock_collection):
    """Test successfully adding a CNAME record."""
    response = client.post(
        "/api/dns",
        json={
            "hostname": "www.example.com",
            "type": "CNAME",
            "value": "example.com"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "www.example.com"
    assert data["type"] == "CNAME"
    assert data["value"] == "example.com"


def test_invalid_record_type(client, mock_collection):
    """Test adding a record with an invalid type."""
    response = client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "MX",  # Not supported
            "value": "mail.example.com"
        }
    )
    assert response.status_code == 400
    assert "Invalid record type" in response.json()["detail"]


def test_cname_conflict_with_existing_records(client, mock_collection):
    """Test that CNAME cannot coexist with other records."""
    # Add an A record first
    client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    
    # Try to add a CNAME for the same hostname
    response = client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "CNAME",
            "value": "other.example.com"
        }
    )
    assert response.status_code == 400
    assert "CNAME cannot coexist with other records" in response.json()["detail"]


def test_a_record_conflict_with_cname(client, mock_collection):
    """Test that A record cannot be added if a CNAME exists."""
    # Add a CNAME record first
    client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "CNAME",
            "value": "other.example.com"
        }
    )
    
    # Try to add an A record for the same hostname
    response = client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    assert response.status_code == 400
    assert "Cannot add A record when CNAME exists" in response.json()["detail"]


def test_duplicate_a_record_prevention(client, mock_collection):
    """Test prevention of duplicate A records."""
    # Add an A record
    client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    
    # Try to add the same A record again
    response = client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    assert response.status_code == 409
    assert "Duplicate A record" in response.json()["detail"]


def test_multiple_a_records_allowed(client, mock_collection):
    """Test that multiple A records with different values are allowed."""
    # Add first A record
    client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    
    # Add second A record with different value
    response = client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.2"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "192.168.1.2"


def test_cname_chaining(client, mock_collection):
    """Test CNAME chaining resolution."""
    # Set up a chain: www -> web -> apex
    client.post(
        "/api/dns",
        json={
            "hostname": "apex.example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    
    client.post(
        "/api/dns",
        json={
            "hostname": "web.example.com",
            "type": "CNAME",
            "value": "apex.example.com"
        }
    )
    
    client.post(
        "/api/dns",
        json={
            "hostname": "www.example.com",
            "type": "CNAME",
            "value": "web.example.com"
        }
    )
    
    # Resolve the chain
    response = client.get("/api/dns/www.example.com")
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "www.example.com"
    assert data["addresses"] == ["192.168.1.1"]


def test_circular_cname_detection(client, mock_collection):
    """Test detection of circular CNAME references."""
    # Create a circular reference: a -> b -> c -> a
    client.post(
        "/api/dns",
        json={
            "hostname": "a.example.com",
            "type": "CNAME",
            "value": "b.example.com"
        }
    )
    
    client.post(
        "/api/dns",
        json={
            "hostname": "b.example.com",
            "type": "CNAME",
            "value": "c.example.com"
        }
    )
    
    client.post(
        "/api/dns",
        json={
            "hostname": "c.example.com",
            "type": "CNAME",
            "value": "a.example.com"
        }
    )
    
    # Try to resolve the circular reference
    response = client.get("/api/dns/a.example.com")
    assert response.status_code == 400
    assert "Circular CNAME detected" in response.json()["detail"]


def test_list_records(client, mock_collection):
    """Test listing records for a hostname."""
    # Create multiple A records
    client.post("/api/dns", json={"hostname": "example.com", "type": "A", "value": "192.168.1.1"})
    client.post("/api/dns", json={"hostname": "example.com", "type": "A", "value": "192.168.1.2"})
    
    # Create records for a different hostname
    client.post("/api/dns", json={"hostname": "other.example.com", "type": "A", "value": "192.168.2.1"})
    
    # List records for the first hostname
    response = client.get("/api/dns/example.com/records")
    assert response.status_code == 200
    data = response.json()
    
    # Check pagination metadata
    assert data["total"] == 2
    assert data["skip"] == 0
    assert data["limit"] == 10
    
    # Check records content
    records = data["records"]
    assert len(records) == 2
    
    # Ensure we only got records for the requested hostname
    for record in records:
        assert record["hostname"] == "example.com"
        assert record["type"] == "A"
        assert record["value"] in ["192.168.1.1", "192.168.1.2"]


def test_list_nonexistent_hostname(client, mock_collection):
    """Test listing records for a hostname that doesn't exist."""
    response = client.get("/api/dns/nonexistent.example.com/records")
    assert response.status_code == 404
    assert "Hostname not found" in response.json()["detail"]


def test_resolve_nonexistent_hostname(client, mock_collection):
    """Test resolving a hostname that doesn't exist."""
    response = client.get("/api/dns/nonexistent.example.com")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_record(client, mock_collection):
    """Test deleting a DNS record."""
    # Create a record
    client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    
    # Delete the record
    response = client.delete(
        "/api/dns/example.com?type=A&value=192.168.1.1"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    
    # Verify record was deleted by trying to resolve it
    response = client.get("/api/dns/example.com")
    assert response.status_code == 404


def test_delete_nonexistent_record(client, mock_collection):
    """Test attempting to delete a record that doesn't exist."""
    response = client.delete(
        "/api/dns/nonexistent.example.com?type=A&value=192.168.1.1"
    )
    assert response.status_code == 404
    assert "record not found" in response.json()["detail"] 