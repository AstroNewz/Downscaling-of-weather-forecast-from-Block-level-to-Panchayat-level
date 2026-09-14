from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Verifies that root '/' returns 200 and points to interactive documentation."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "GraminKrishi" in data["app_name"]
    assert data["documentation_url"] == "/docs"


def test_health_liveness_endpoint(client: TestClient):
    """Verifies that '/api/v1/health' returns healthy status and system components."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert json_resp["data"]["status"] == "healthy"
    assert "components" in json_resp["data"]
    assert json_resp["data"]["components"]["api_server"]["status"] == "healthy"


def test_health_readiness_endpoint(client: TestClient):
    """Verifies that '/api/v1/health/ready' returns ready status."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    json_resp = response.json()
    assert json_resp["success"] is True
    assert json_resp["data"]["status"] == "ready"


def test_process_time_header(client: TestClient):
    """Verifies that the custom diagnostic X-Process-Time-Seconds header is included."""
    response = client.get("/api/v1/health")
    assert "x-process-time-seconds" in response.headers
