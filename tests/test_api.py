from fastapi.testclient import TestClient

from app.main import create_app


def client(tmp_path, network_cooldown=0):
    return TestClient(create_app(tmp_path / "fennec.db", network_cooldown=network_cooldown))


def test_health_and_modules(tmp_path):
    api = client(tmp_path)
    health = api.get("/api/health")
    assert health.status_code == 200
    assert health.json()["data"]["storage"] == "sqlite"
    modules = api.get("/api/modules").json()["data"]
    by_id = {item["id"]: item for item in modules}
    assert by_id["phone"]["available"] is True
    assert by_id["email"]["available"] is True
    assert by_id["domain"]["available"] is True
    assert by_id["username"]["available"] is True
    assert by_id["metadata"]["available"] is True
    assert by_id["metadata"]["input_kind"] == "file"
    assert by_id["company"]["available"] is True
    assert by_id["geoip"]["network"] is False
    assert "RDAP" in by_id["domain"]["summary"]


def test_case_and_phone_run(tmp_path):
    api = client(tmp_path)
    created = api.post("/api/cases", json={"name": "Desk check", "notes": "local"})
    assert created.status_code == 201
    case_id = created.json()["data"]["id"]

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


def fake_dns(_host):
    return {
        "A": ["93.184.216.34"],
        "AAAA": [],
        "MX": ["0 ."],
        "NS": ["a.iana-servers.net."],
        "TXT": ["v=spf1 -all"],
    }


def fake_whois(_host):
    return {
        "registrar": "RESERVED-Internet Assigned Numbers Authority",
        "registrant": "",
        "registrant_country": "US",
        "creation_date": "1995-08-14T04:00:00+00:00",
        "expiration_date": "2026-08-13T04:00:00+00:00",
        "updated_date": "",
        "name_servers": ["a.iana-servers.net"],
        "emails": [],
        "status": "clientHold",
        "source": "rdap",
    }


def test_domain_run_uses_injected_lookups(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.domain.lookup_dns", fake_dns)
    monkeypatch.setattr("app.modules.domain.lookup_whois", fake_whois)
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Host"})
    run = api.post("/api/cases/1/runs", json={"module": "domain", "value": "https://www.example.com/path"})
    assert run.status_code == 201
    body = run.json()["data"]
    assert body["status"] == "ok"
    kinds = {(item["kind"], item["value"]) for item in body["findings"]}
    assert ("domain", "example.com") in kinds
    assert ("ip", "93.184.216.34") in kinds
    assert ("registrar", "RESERVED-Internet Assigned Numbers Authority") in kinds
    assert ("country", "US") in kinds


def test_bad_domain_is_a_failed_run(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.domain.lookup_dns", fake_dns)
    monkeypatch.setattr("app.modules.domain.lookup_whois", fake_whois)
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Bad host"})
    run = api.post("/api/cases/1/runs", json={"module": "domain", "value": "not a domain"})
    assert run.status_code == 201
    assert run.json()["data"]["status"] == "failed"
    assert run.json()["data"]["findings"] == []


def test_metadata_and_export(tmp_path):
    from PIL import Image

    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Photo"})
    image_path = tmp_path / "shot.jpg"
    Image.new("RGB", (8, 8), "red").save(image_path, "JPEG")
    with image_path.open("rb") as handle:
        run = api.post(
            "/api/cases/1/runs",
            data={"module": "metadata"},
            files={"file": ("shot.jpg", handle, "image/jpeg")},
        )
    assert run.status_code == 201
    kinds = {item["kind"] for item in run.json()["data"]["findings"]}
    assert "file" in kinds
    assert "hash" in kinds
    dossier = api.get("/api/cases/1/export")
    assert dossier.status_code == 200
    assert dossier.json()["data"]["name"] == "Photo"
    html = api.get("/api/cases/1/export.html")
    assert html.status_code == 200
    assert "Photo" in html.text


def test_repeat_domain_is_limited(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.domain.lookup_dns", fake_dns)
    monkeypatch.setattr("app.modules.domain.lookup_whois", fake_whois)
    api = client(tmp_path, network_cooldown=60)
    api.post("/api/cases", json={"name": "Repeat"})
    first = api.post("/api/cases/1/runs", json={"module": "domain", "value": "example.com"})
    second = api.post("/api/cases/1/runs", json={"module": "domain", "value": "example.com"})
    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "network_limited"


def fake_username(_user):
    return [
        {
            "name": "github",
            "url": "https://github.com/octocat",
            "status": 200,
            "exists": True,
            "error": None,
        },
        {
            "name": "gitlab",
            "url": "https://gitlab.com/octocat",
            "status": 404,
            "exists": False,
            "error": None,
        },
        {
            "name": "reddit",
            "url": "https://www.reddit.com/user/octocat",
            "status": 403,
            "exists": False,
            "error": None,
        },
    ]


def test_username_run_uses_injected_scanner(tmp_path, monkeypatch):
    monkeypatch.setattr("app.modules.username.scan_username", fake_username)
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Handle"})
    run = api.post("/api/cases/1/runs", json={"module": "username", "value": "@octocat"})
    assert run.status_code == 201
    body = run.json()["data"]
    assert body["status"] == "ok"
    kinds = {(item["kind"], item["value"]) for item in body["findings"]}
    assert ("username", "octocat") in kinds
    assert ("account", "https://github.com/octocat") in kinds
    assert ("rate_limit", "reddit") in kinds
    assert ("account", "https://gitlab.com/octocat") not in kinds


def test_correlation_links_shared_domain(tmp_path):
    from app import db

    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Overlap"})
    path = tmp_path / "fennec.db"
    db.add_run(
        path,
        1,
        "domain",
        "ok",
        "example.com",
        None,
        [
            {
                "kind": "domain",
                "value": "example.com",
                "source": "test",
                "confidence": "high",
                "evidence": "",
            }
        ],
    )
    db.add_run(
        path,
        1,
        "email",
        "ok",
        "ada@example.com",
        None,
        [
            {
                "kind": "email",
                "value": "ada@example.com",
                "source": "test",
                "confidence": "high",
                "evidence": "",
            }
        ],
    )
    links = api.get("/api/cases/1").json()["data"]["links"]
    assert any(item["kind"] == "domain" and item["value"] == "example.com" and item["count"] == 2 for item in links)


def test_run_timeout_stays_readable(tmp_path, monkeypatch):
    import time

    def hang(_module, _value):
        time.sleep(2)
        raise AssertionError("should have been cancelled")

    monkeypatch.setattr("app.main.execute", hang)
    api = TestClient(create_app(tmp_path / "fennec.db", network_cooldown=0, run_timeout=0.1))
    api.post("/api/cases", json={"name": "Slow"})
    run = api.post("/api/cases/1/runs", json={"module": "phone", "value": "+41446681800"})
    assert run.status_code == 201
    assert run.json()["data"]["status"] == "failed"
    assert "Timed out" in run.json()["data"]["error"]
    assert api.get("/api/cases/1").status_code == 200


def test_geoip_and_company_and_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.modules.geoip.lookup_ip",
        lambda _ip: {"country": "Australia", "iso": "AU", "city": "", "source": "test.mmdb"},
    )
    monkeypatch.setattr(
        "app.modules.company.search_wikidata",
        lambda _name: {
            "hits": [
                {"id": "Q95", "label": "Google", "description": "American technology company"},
                {"id": "Q9366", "label": "Alphabet", "description": "holding company"},
            ],
            "entity": {
                "labels": {"en": {"value": "Google"}},
                "descriptions": {"en": {"value": "American technology company"}},
                "claims": {
                    "P856": [{"mainsnak": {"datavalue": {"value": "https://www.google.com/"}}}]
                },
            },
        },
    )
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Org"})
    geo = api.post("/api/cases/1/runs", json={"module": "geoip", "value": "1.1.1.1"})
    assert geo.status_code == 201
    assert ("country", "Australia") in {(i["kind"], i["value"]) for i in geo.json()["data"]["findings"]}
    missing = api.post("/api/cases/1/runs", json={"module": "geoip", "value": "not-an-ip"})
    assert missing.json()["data"]["status"] == "failed"
    company = api.post("/api/cases/1/runs", json={"module": "company", "value": "Google"})
    assert company.status_code == 201
    kinds = {(i["kind"], i["value"]) for i in company.json()["data"]["findings"]}
    assert ("company", "Google") in kinds
    assert ("wikidata", "Q95") in kinds
    assert ("url", "https://www.google.com/") in kinds
    pdf = api.get("/api/cases/1/export.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_geoip_without_database_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("FENNEC_GEOLITE", raising=False)
    monkeypatch.chdir(tmp_path)
    from app.modules.geoip import run

    result = run("8.8.8.8")
    assert result.status == "failed"
    assert "GeoIP database" in (result.error or "")


def test_home_shell(tmp_path):
    response = client(tmp_path).get("/")
    assert response.status_code == 200
    assert "Fennec" in response.text
    assert "/static/favicon.svg" in response.text
    assert "/static/app.js" in response.text


def test_select_sites_keeps_a_small_set():
    from types import SimpleNamespace

    from app.modules.email import select_sites

    sites = [SimpleNamespace(__name__=name) for name in ("github", "pornhub", "twitter")]
    names = {item.__name__ for item in select_sites(sites)}
    assert names == {"github", "twitter"}
