from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Fennec"
    assert body["milestone"] == "M0"


def test_home_names_fennec():
    response = client.get("/")
    assert response.status_code == 200
    assert "Fennec" in response.text
    assert "Maigret" in response.text
