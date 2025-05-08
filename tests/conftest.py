"""
Pytest configuration file for shared fixtures.

This module contains fixtures that are shared across multiple test files
to avoid code duplication and ensure consistent test setup.
"""

import asyncio
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import mongomock
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def reset_event_loop():
    """Ensure a clean asyncio event loop is available."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

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