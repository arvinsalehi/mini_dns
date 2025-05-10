"""
Pytest configuration file for shared fixtures.

This module contains fixtures that are shared across multiple test files
to avoid code duplication and ensure consistent test setup.
"""

import contextlib
from starlette.testclient import TestClient
import pytest
from unittest.mock import MagicMock, patch
import mongomock
from app.main import app
from tests.util.wrapper import AsyncMongoMockCollection


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    # Set raise_server_exceptions=True to see the actual server errors
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


# Make sure ALL database calls are properly mocked with our async-compatible wrapper
@pytest.fixture
def mock_collection():
    """Set up a mock MongoDB collection for testing."""
    
    collection = mongomock.MongoClient().db.collection
    async_collection = AsyncMongoMockCollection(collection)
    
    # Target all places where get_dns_collection might be called
    with contextlib.ExitStack() as stack:
        # Mock in app.routers.dns
        stack.enter_context(patch('app.routers.dns.get_dns_collection', return_value=async_collection))
        # Also mock the original function to catch any direct imports
        stack.enter_context(patch('app.db.connectors.get_dns_collection', return_value=async_collection))
        # Mock the MongoConnector to prevent any real connections
        stack.enter_context(patch('app.db.connectors.MongoConnector.get_client', return_value=MagicMock()))
        
        # Clear collection before each test
        collection.delete_many({})
        
        yield async_collection
