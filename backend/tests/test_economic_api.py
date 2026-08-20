"""
Pruebas de integración para endpoints económicos (/api/v1/economic).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_economic_context():
    response = client.get("/api/v1/economic/context")
    assert response.status_code == 200
    data = response.json()
    assert "last_updated" in data


def test_get_inflation_history_monthly():
    response = client.get("/api/v1/economic/inflation/history?granularity=monthly")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_inflation_history_yearly():
    response = client.get("/api/v1/economic/inflation/history?granularity=yearly")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
