"""
Integration tests for FastAPI REST API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "Auto-QA PR Sentinel"
    assert data["concurrency"] == 4
    assert data["rag_documents_indexed"] >= 5

def test_scenarios_endpoint(client):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 4
    categories = [s["category"] for s in scenarios]
    assert "SECURITY" in categories
    assert "RELIABILITY" in categories
    assert "CLEAN" in categories

def test_rag_search_endpoint(client):
    response = client.post("/api/rag/search", json={
        "query": "SQL injection parameterized query prevention",
        "top_k": 2
    })
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0
    assert "metrics" in data
    assert data["metrics"]["context_relevance"] > 0

def test_direct_sandbox_endpoint(client):
    response = client.post("/api/sandbox/test", json={
        "code": "def add(x, y): return x + y",
        "test_code": "from module import add\ndef test_add(): assert add(1, 2) == 3",
        "filename": "module.py"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["tests_passed"] == 1
