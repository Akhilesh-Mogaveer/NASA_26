"""Tests for FireLens Health and Root endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns success message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "FireLens API is running" in data["message"]
    assert "docs_url" in data


def test_api_health_endpoint():
    """Verify that /api/health returns healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "FireLens API"
    assert "version" in data
    assert "timestamp" in data
    assert "data_directories" in data
    # Verify core data directories are detected
    assert data["data_directories"]["data_dir"] is True
    assert data["data_directories"]["processed"] is True


def test_platform_health_endpoint():
    """Verify standard /health endpoint for deployment health probes."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
