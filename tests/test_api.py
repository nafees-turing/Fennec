from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path):
    return TestClient(create_app(tmp_path / "fennec.db"))


def test_health_and_modules(tmp_path):
    api = client(tmp_path)
    health = api.get("/api/health")
    assert health.status_code == 200
    assert health.json()["data"]["storage"] == "sqlite"
    modules = api.get("/api/modules").json()["data"]
    by_id = {item["id"]: item for item in modules}
    assert by_id["phone"]["available"] is True
    assert by_id["email"]["available"] is True
    assert by_id["username"]["available"] is False
    assert by_id["domain"]["summary"].find("whoisdomain") >= 0


def test_case_and_phone_run(tmp_path):
    api = client(tmp_path)
    created = api.post("/api/cases", json={"name": "Desk check", "notes": "local"})
    assert created.status_code == 201
    case_id = created.json()["data"]["id"]

    blocked = api.post("/api/cases/1/runs", json={"module": "username", "value": "ada"})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "module_unavailable"

    run = api.post("/api/cases/1/runs", json={"module": "phone", "value": "+41446681800"})
    assert run.status_code == 201
    body = run.json()["data"]
    assert body["status"] == "ok"
    kinds = {item["kind"] for item in body["findings"]}
    assert "phone" in kinds

    detail = api.get(f"/api/cases/{case_id}").json()["data"]
    assert detail["name"] == "Desk check"
    assert len(detail["findings"]) >= 1
    assert detail["runs"][0]["module_id"] == "phone"


def test_bad_phone_is_a_failed_run(tmp_path):
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Bad number"})
    run = api.post("/api/cases/1/runs", json={"module": "phone", "value": "not-a-number"})
    assert run.status_code == 201
    assert run.json()["data"]["status"] == "failed"
    assert run.json()["data"]["findings"] == []


def fake_sites(_email):
    return [
        {
            "name": "github",
            "domain": "github.com",
            "exists": True,
            "rateLimit": False,
            "emailrecovery": "a***@example.com",
            "phoneNumber": None,
            "others": None,
        },
        {
            "name": "twitter",
            "domain": "twitter.com",
            "exists": False,
            "rateLimit": False,
            "emailrecovery": None,
            "phoneNumber": None,
            "others": None,
        },
        {
            "name": "snapchat",
            "domain": "snapchat.com",
            "exists": False,
            "rateLimit": True,
            "emailrecovery": None,
            "phoneNumber": None,
            "others": None,
        },
    ]


def test_email_run_uses_injected_scanner(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.email.scan_sites", fake_sites)
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Inbox"})
    run = api.post("/api/cases/1/runs", json={"module": "email", "value": "Ada@Example.com"})
    assert run.status_code == 201
    body = run.json()["data"]
    assert body["status"] == "ok"
    kinds = {(item["kind"], item["value"]) for item in body["findings"]}
    assert ("email", "ada@example.com") in kinds
    assert ("account", "github.com") in kinds
    assert ("rate_limit", "snapchat.com") in kinds
    assert ("account", "twitter.com") not in kinds


def test_bad_email_is_a_failed_run(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.email.scan_sites", fake_sites)
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Bad mail"})
    run = api.post("/api/cases/1/runs", json={"module": "email", "value": "not-an-email"})
    assert run.status_code == 201
    assert run.json()["data"]["status"] == "failed"
    assert run.json()["data"]["findings"] == []


def test_home_shell(tmp_path):
    response = client(tmp_path).get("/")
    assert response.status_code == 200
    assert "Fennec" in response.text
    assert "/static/app.js" in response.text
