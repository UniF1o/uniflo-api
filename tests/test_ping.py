from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_service_ping():
    response = client.head("/ping")
    assert response.status_code == 200
