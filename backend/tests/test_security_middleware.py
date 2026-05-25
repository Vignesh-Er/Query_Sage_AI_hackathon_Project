import pytest
from starlette.testclient import TestClient
from app.main import app

def test_host_header_dns_rebinding_rejected():
    client = TestClient(app)
    
    # 1. Spoofed Host header (attacker.com) -> Expected: 400 Bad Request
    response = client.get("/api/connections", headers={"Host": "attacker.com"})
    assert response.status_code == 400
    
def test_host_header_localhost_allowed():
    client = TestClient(app)
    
    # 2. Authorized Host header (localhost) -> Expected: Not 400 (e.g., 200, 401, or other based on authentication)
    # The route might return 200 if seeded or empty list, but it should not return 400.
    response = client.get("/api/connections", headers={"Host": "localhost"})
    assert response.status_code != 400
