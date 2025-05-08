"""
NOTE Generated via Cursor running on claude-3.7-sonnet. Supervised by Arvin Salehi.

Integration tests for the DNS service.

This module tests the complete workflow of the DNS service, focusing on:
1. End-to-end functionality
2. Integration between components
3. Complex scenarios involving multiple operations
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
import mongomock


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


def test_complete_dns_workflow(client, mock_collection):
    """Test a complete workflow including create, read, resolve, and delete operations."""
    # 1. Create multiple records
    hostnames = ["example.com", "www.example.com", "api.example.com"]
    
    # Add A records for the main domain
    response = client.post(
        "/api/dns",
        json={
            "hostname": hostnames[0],
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    assert response.status_code == 200
    
    response = client.post(
        "/api/dns",
        json={
            "hostname": hostnames[0],
            "type": "A",
            "value": "192.168.1.2"
        }
    )
    assert response.status_code == 200
    
    # Add CNAME for www subdomain
    response = client.post(
        "/api/dns",
        json={
            "hostname": hostnames[1],
            "type": "CNAME",
            "value": hostnames[0]
        }
    )
    assert response.status_code == 200
    
    # Add A record for api subdomain
    response = client.post(
        "/api/dns",
        json={
            "hostname": hostnames[2],
            "type": "A",
            "value": "192.168.2.1"
        }
    )
    assert response.status_code == 200
    
    # 2. List and verify records
    for hostname in hostnames:
        response = client.get(f"/api/dns/{hostname}/records")
        assert response.status_code == 200
        data = response.json()
        records = data["records"]
        
        if hostname == hostnames[0]:  # example.com
            assert len(records) == 2
            values = [r.get("value") for r in records]
            assert "192.168.1.1" in values
            assert "192.168.1.2" in values
        elif hostname == hostnames[1]:  # www.example.com
            assert len(records) == 1
            assert records[0].get("type") == "CNAME"
            assert records[0].get("value") == hostnames[0]
        elif hostname == hostnames[2]:  # api.example.com
            assert len(records) == 1
            assert records[0].get("type") == "A"
            assert records[0].get("value") == "192.168.2.1"
    
    # 3. Resolve hostnames
    # Resolve example.com (should return both A records)
    response = client.get(f"/api/dns/{hostnames[0]}")
    assert response.status_code == 200
    result = response.json()
    assert result.get("hostname") == hostnames[0]
    assert sorted(result.get("addresses")) == sorted(["192.168.1.1", "192.168.1.2"])
    
    # Resolve www.example.com (should follow CNAME to example.com)
    response = client.get(f"/api/dns/{hostnames[1]}")
    assert response.status_code == 200
    result = response.json()
    assert result.get("hostname") == hostnames[1]
    assert sorted(result.get("addresses")) == sorted(["192.168.1.1", "192.168.1.2"])
    
    # Resolve api.example.com (should return its A record)
    response = client.get(f"/api/dns/{hostnames[2]}")
    assert response.status_code == 200
    result = response.json()
    assert result.get("hostname") == hostnames[2]
    assert result.get("addresses") == ["192.168.2.1"]
    
    # 4. Delete records and verify deletion
    # Delete one A record from example.com
    response = client.delete(f"/api/dns/{hostnames[0]}?type=A&value=192.168.1.1")
    assert response.status_code == 200
    
    # Verify the record was deleted
    response = client.get(f"/api/dns/{hostnames[0]}/records")
    assert response.status_code == 200
    data = response.json()
    records = data["records"]
    assert len(records) == 1
    assert records[0].get("value") == "192.168.1.2"
    
    # Delete the CNAME record
    response = client.delete(f"/api/dns/{hostnames[1]}?type=CNAME&value={hostnames[0]}")
    assert response.status_code == 200
    
    # Verify the CNAME was deleted
    response = client.get(f"/api/dns/{hostnames[1]}/records")
    assert response.status_code == 404


def test_complex_cname_chain(client, mock_collection):
    """Test a complex CNAME chain with multiple levels."""
    # Create a chain of CNAMEs:
    # level3.example.com -> level2.example.com -> level1.example.com -> example.com
    
    # Create the target A record
    client.post(
        "/api/dns",
        json={
            "hostname": "example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    
    # Create the CNAME chain
    cnames = [
        {"hostname": "level1.example.com", "target": "example.com"},
        {"hostname": "level2.example.com", "target": "level1.example.com"},
        {"hostname": "level3.example.com", "target": "level2.example.com"}
    ]
    
    for cname in cnames:
        response = client.post(
            "/api/dns",
            json={
                "hostname": cname["hostname"],
                "type": "CNAME",
                "value": cname["target"]
            }
        )
        assert response.status_code == 200
    
    # Resolve the end of the chain
    response = client.get("/api/dns/level3.example.com")
    assert response.status_code == 200
    result = response.json()
    assert result.get("hostname") == "level3.example.com"
    assert result.get("addresses") == ["192.168.1.1"]
    
    # Delete a link in the middle of the chain
    response = client.delete("/api/dns/level2.example.com?type=CNAME&value=level1.example.com")
    assert response.status_code == 200
    
    # Resolving should now fail
    response = client.get("/api/dns/level3.example.com")
    assert response.status_code == 404


def test_error_condition_handling(client, mock_collection):
    """Test handling of various error conditions."""
    # Test record not found
    response = client.get("/api/dns/nonexistent.example.com")
    assert response.status_code == 404
    
    # Test deletion of non-existent record
    response = client.delete("/api/dns/nonexistent.example.com?type=A&value=192.168.1.1")
    assert response.status_code == 404
    
    # Test conflicting record types
    # Create CNAME record
    client.post(
        "/api/dns",
        json={
            "hostname": "conflict.example.com",
            "type": "CNAME",
            "value": "example.com"
        }
    )
    
    # Try to add A record for same hostname
    response = client.post(
        "/api/dns",
        json={
            "hostname": "conflict.example.com",
            "type": "A",
            "value": "192.168.1.1"
        }
    )
    assert response.status_code == 400
    assert "Cannot add A record when CNAME exists" in response.json()["detail"]
    
    # Create circular reference
    responses = []
    responses.append(client.post(
        "/api/dns",
        json={
            "hostname": "circular1.example.com",
            "type": "CNAME",
            "value": "circular2.example.com"
        }
    ))
    
    responses.append(client.post(
        "/api/dns",
        json={
            "hostname": "circular2.example.com",
            "type": "CNAME",
            "value": "circular1.example.com"
        }
    ))
    
    # Make sure creation succeeded
    for r in responses:
        assert r.status_code == 200
    
    # Test circular reference detection
    response = client.get("/api/dns/circular1.example.com")
    assert response.status_code == 400
    assert "Circular CNAME detected" in response.json()["detail"] 