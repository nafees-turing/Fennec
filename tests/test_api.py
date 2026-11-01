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
    assert by_id["email"]["category"] == "basic"
    assert by_id["social"]["category"] == "social"
    assert by_id["address"]["category"] == "addresses"
    assert by_id["domain"]["category"] == "network"
    assert by_id["certs"]["category"] == "network"
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


def test_private_ip_scope_needs_no_database(tmp_path, monkeypatch):
    monkeypatch.delenv("FENNEC_GEOLITE", raising=False)
    monkeypatch.delenv("FENNEC_ASN", raising=False)
    monkeypatch.chdir(tmp_path)
    from app.modules import geoip

    monkeypatch.setattr(geoip, "asn_path", lambda: tmp_path / "missing-asn.mmdb")
    monkeypatch.setattr(geoip, "database_path", lambda: tmp_path / "missing-geo.mmdb")
    result = geoip.run("10.1.2.3")
    assert result.status == "ok"
    kinds = {(item.kind, item.value) for item in result.findings}
    assert ("ip", "10.1.2.3") in kinds
    assert ("scope", "private") in kinds


def test_asn_from_netwatch_db_if_present():
    from app.modules.geoip import asn_path, run

    if not asn_path().is_file():
        return
    result = run("1.1.1.1")
    assert result.status == "ok"
    asns = {item.value for item in result.findings if item.kind == "asn"}
    assert "AS13335" in asns


def test_name_address_social_certs_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.modules.social.scan_social",
        lambda _user: [
            {"name": "reddit", "url": "https://www.reddit.com/user/ada", "status": 200, "exists": True, "error": None},
            {"name": "tiktok", "url": "https://www.tiktok.com/@ada", "status": 404, "exists": False, "error": None},
        ],
    )
    monkeypatch.setattr("app.modules.certs.fetch_certs", lambda _host: ["www.example.com", "mail.example.com"])
    monkeypatch.setattr(
        "app.modules.archive.fetch_archive",
        lambda _host: {
            "available": True,
            "url": "https://web.archive.org/web/20200101000000/https://example.com/",
            "timestamp": "20200101000000",
            "status": "200",
        },
    )
    api = client(tmp_path)
    api.post("/api/cases", json={"name": "Kit"})
    name = api.post("/api/cases/1/runs", json={"module": "name", "value": "Ada Lovelace"})
    assert name.status_code == 201
    assert ("name", "Ada Lovelace") in {(i["kind"], i["value"]) for i in name.json()["data"]["findings"]}
    place = api.post("/api/cases/1/runs", json={"module": "address", "value": "221B Baker Street, London"})
    assert place.status_code == 201
    social = api.post("/api/cases/1/runs", json={"module": "social", "value": "ada"})
    assert ("account", "https://www.reddit.com/user/ada") in {
        (i["kind"], i["value"]) for i in social.json()["data"]["findings"]
    }
    certs = api.post("/api/cases/1/runs", json={"module": "certs", "value": "example.com"})
    assert ("cert_name", "www.example.com") in {(i["kind"], i["value"]) for i in certs.json()["data"]["findings"]}
    archive = api.post("/api/cases/1/runs", json={"module": "archive", "value": "example.com"})
    assert archive.status_code == 201
    assert any(i["kind"] == "url" and "web.archive.org" in i["value"] for i in archive.json()["data"]["findings"])
    monkeypatch.setattr("app.modules.rdns.lookup_ptr", lambda _ip: ["one.one.one.one"])
    monkeypatch.setattr(
        "app.modules.internetdb.fetch_internetdb",
        lambda _ip: {"hostnames": ["one.one.one.one"], "ports": [53, 443], "cpes": [], "vulns": []},
    )
    monkeypatch.setattr(
        "app.modules.github.fetch_user",
        lambda _login: {
            "login": "octocat",
            "html_url": "https://github.com/octocat",
            "name": "The Octocat",
            "blog": "https://github.blog",
            "email": None,
            "bio": "GitHub mascot",
            "company": "GitHub",
            "location": "San Francisco",
        },
    )
    monkeypatch.setattr(
        "app.modules.bitcoin.fetch_address",
        lambda _addr: {"chain_stats": {"funded_txo_sum": 1000, "spent_txo_sum": 200, "tx_count": 3}},
    )
    ptr = api.post("/api/cases/1/runs", json={"module": "rdns", "value": "1.1.1.1"})
    assert ("hostname", "one.one.one.one") in {(i["kind"], i["value"]) for i in ptr.json()["data"]["findings"]}
    idb = api.post("/api/cases/1/runs", json={"module": "internetdb", "value": "1.1.1.1"})
    assert ("port", "443") in {(i["kind"], i["value"]) for i in idb.json()["data"]["findings"]}
    gh = api.post("/api/cases/1/runs", json={"module": "github", "value": "octocat"})
    assert ("name", "The Octocat") in {(i["kind"], i["value"]) for i in gh.json()["data"]["findings"]}
    btc = api.post(
        "/api/cases/1/runs",
        json={"module": "bitcoin", "value": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"},
    )
    assert btc.status_code == 201
    assert any(i["kind"] == "balance" for i in btc.json()["data"]["findings"])
    monkeypatch.setattr(
        "app.modules.gravatar.fetch_profile",
        lambda _email: {"hash": "abc", "entry": {"displayName": "Ada", "profileUrl": "https://gravatar.com/ada", "accounts": []}},
    )
    monkeypatch.setattr(
        "app.modules.sanctions.search_sanctions",
        lambda _q: [{"caption": "Example Ltd", "schema": "Company", "id": "ex-1"}],
    )
    monkeypatch.setattr(
        "app.modules.bgp.fetch_bgp",
        lambda _ip: {"prefixes": [{"prefix": "1.1.1.0/24", "asn": {"asn": 13335, "name": "CLOUDFLARENET"}}], "rir_allocation": {"rir_name": "ARIN"}},
    )
    monkeypatch.setattr(
        "app.modules.ethereum.fetch_address",
        lambda _addr: {"name": None, "coin_balance": "1", "is_contract": False},
    )
    monkeypatch.setattr(
        "app.modules.person.search_wikidata",
        lambda _name: {"hits": [{"id": "Q7259", "label": "Ada Lovelace", "description": "mathematician"}], "entity": {"labels": {"en": {"value": "Ada Lovelace"}}, "descriptions": {"en": {"value": "mathematician"}}, "claims": {}}},
    )
    grav = api.post("/api/cases/1/runs", json={"module": "gravatar", "value": "ada@example.com"})
    assert grav.status_code == 201
    san = api.post("/api/cases/1/runs", json={"module": "sanctions", "value": "Example Ltd"})
    assert ("sanction", "Example Ltd") in {(i["kind"], i["value"]) for i in san.json()["data"]["findings"]}
    bgp = api.post("/api/cases/1/runs", json={"module": "bgp", "value": "1.1.1.1"})
    assert ("asn", "AS13335") in {(i["kind"], i["value"]) for i in bgp.json()["data"]["findings"]}
    eth = api.post("/api/cases/1/runs", json={"module": "ethereum", "value": "0x" + "a" * 40})
    assert eth.status_code == 201
    person = api.post("/api/cases/1/runs", json={"module": "person", "value": "Ada Lovelace"})
    assert ("wikidata", "Q7259") in {(i["kind"], i["value"]) for i in person.json()["data"]["findings"]}
    monkeypatch.setattr(
        "app.modules.greynoise.fetch_community",
        lambda _ip: {"status": 200, "body": {"classification": "benign", "riot": True, "name": "Cloudflare", "link": "https://viz.greynoise.io/riot/1.1.1.1"}},
    )
    monkeypatch.setattr(
        "app.modules.geocode.search_place",
        lambda _q: [{"display_name": "Baker Street, London", "lat": "51.52", "lon": "-0.16", "type": "road", "class": "highway"}],
    )
    monkeypatch.setattr(
        "app.modules.securitytxt.fetch_securitytxt",
        lambda _h: "Contact: mailto:security@example.com\nPolicy: https://example.com/security\n",
    )
    monkeypatch.setattr(
        "app.modules.gitlab.fetch_user",
        lambda _u: {"username": "ada", "name": "Ada", "web_url": "https://gitlab.com/ada", "location": ""},
    )
    monkeypatch.setattr(
        "app.modules.keybase.fetch_user",
        lambda _u: {
            "status": {"code": 0},
            "them": {
                "basics": {"username": "ada"},
                "profile": {"full_name": "Ada L", "location": "", "bio": ""},
                "proofs_summary": {"all": [{"nametag": "ada", "proof_type": "github", "service_url": "https://github.com/ada"}]},
            },
        },
    )
    gn = api.post("/api/cases/1/runs", json={"module": "greynoise", "value": "1.1.1.1"})
    assert ("org", "Cloudflare") in {(i["kind"], i["value"]) for i in gn.json()["data"]["findings"]}
    geo = api.post("/api/cases/1/runs", json={"module": "geocode", "value": "221B Baker Street, London"})
    assert ("coords", "51.52,-0.16") in {(i["kind"], i["value"]) for i in geo.json()["data"]["findings"]}
    st = api.post("/api/cases/1/runs", json={"module": "securitytxt", "value": "example.com"})
    assert ("email", "security@example.com") in {(i["kind"], i["value"]) for i in st.json()["data"]["findings"]}
    gl = api.post("/api/cases/1/runs", json={"module": "gitlab", "value": "ada"})
    assert ("url", "https://gitlab.com/ada") in {(i["kind"], i["value"]) for i in gl.json()["data"]["findings"]}
    kb = api.post("/api/cases/1/runs", json={"module": "keybase", "value": "ada"})
    assert kb.status_code == 201
    monkeypatch.setattr("app.modules.npm.fetch_user", lambda _u: {"name": "ada", "email": "ada@npm.test", "homepage": "https://example.com"})
    monkeypatch.setattr("app.modules.dockerhub.fetch_user", lambda _u: {"username": "ada", "full_name": "Ada", "location": "", "company": ""})
    monkeypatch.setattr("app.modules.hackernews.fetch_user", lambda _u: {"id": "ada", "karma": 1, "about": "hi"})
    monkeypatch.setattr("app.modules.reddit.fetch_user", lambda _u: {"name": "ada", "subreddit": {"title": "Ada", "public_description": ""}, "total_karma": 2})
    monkeypatch.setattr("app.modules.wikipedia.fetch_summary", lambda _t: {"title": "Ada Lovelace", "description": "mathematician", "extract": "Ada wrote notes.", "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}}})
    monkeypatch.setattr("app.modules.pgp.fetch_key", lambda _e: {"found": True, "text": "BEGIN"})
    monkeypatch.setattr("app.modules.otx.fetch_indicator", lambda _ip: {"pulse_info": {"count": 3}, "reputation": 0, "country_name": "Australia", "asn": "AS13335"})
    assert api.post("/api/cases/1/runs", json={"module": "npm", "value": "ada"}).status_code == 201
    assert api.post("/api/cases/1/runs", json={"module": "dockerhub", "value": "ada"}).status_code == 201
    assert api.post("/api/cases/1/runs", json={"module": "hackernews", "value": "ada"}).status_code == 201
    assert api.post("/api/cases/1/runs", json={"module": "reddit", "value": "ada"}).status_code == 201
    wiki = api.post("/api/cases/1/runs", json={"module": "wikipedia", "value": "Ada Lovelace"})
    assert ("url", "https://en.wikipedia.org/wiki/Ada_Lovelace") in {(i["kind"], i["value"]) for i in wiki.json()["data"]["findings"]}
    assert api.post("/api/cases/1/runs", json={"module": "pgp", "value": "ada@example.com"}).status_code == 201
    otx = api.post("/api/cases/1/runs", json={"module": "otx", "value": "1.1.1.1"})
    assert ("country", "Australia") in {(i["kind"], i["value"]) for i in otx.json()["data"]["findings"]}
    monkeypatch.setattr("app.modules.chess.fetch_player", lambda _u: {"username": "ada", "name": "Ada", "url": "https://www.chess.com/member/ada", "location": "", "country": "", "title": ""})
    monkeypatch.setattr("app.modules.lichess.fetch_user", lambda _u: {"username": "ada", "profile": {"realName": "Ada", "location": "", "bio": "", "links": ""}})
    monkeypatch.setattr("app.modules.stackoverflow.search_users", lambda _q: [{"display_name": "Ada", "link": "https://stackoverflow.com/users/1/ada", "location": "", "website_url": ""}])
    monkeypatch.setattr("app.modules.devto.fetch_user", lambda _u: {"username": "ada", "name": "Ada", "summary": "", "location": "", "website_url": "", "twitter_username": None, "github_username": None})
    assert api.post("/api/cases/1/runs", json={"module": "chess", "value": "ada"}).status_code == 201
    assert api.post("/api/cases/1/runs", json={"module": "lichess", "value": "ada"}).status_code == 201
    assert api.post("/api/cases/1/runs", json={"module": "stackoverflow", "value": "Ada"}).status_code == 201
    assert api.post("/api/cases/1/runs", json={"module": "devto", "value": "ada"}).status_code == 201


def test_detect_and_smart_phone_lookup(tmp_path):
    api = client(tmp_path)
    email = api.get("/api/detect", params={"q": "Ada@Example.com"})
    assert email.json()["data"]["detected"] == "email"
    modules = [item["module"] for item in email.json()["data"]["matches"]]
    assert modules == ["email", "domain", "gravatar", "pgp"]
    phone = api.get("/api/detect", params={"q": "+41446681800"})
    assert phone.json()["data"]["detected"] == "phone"
    handle = api.get("/api/detect", params={"q": "@octocat"})
    assert [item["module"] for item in handle.json()["data"]["matches"]] == [
        "username",
        "social",
        "github",
        "gitlab",
        "keybase",
        "npm",
        "dockerhub",
        "hackernews",
        "reddit",
        "chess",
        "lichess",
        "stackoverflow",
        "devto",
    ]
    ip = api.get("/api/detect", params={"q": "1.1.1.1"})
    assert [item["module"] for item in ip.json()["data"]["matches"]] == [
        "geoip",
        "rdns",
        "internetdb",
        "bgp",
        "greynoise",
        "otx",
    ]
    api.post("/api/cases", json={"name": "Auto"})
    run = api.post("/api/cases/1/lookup", json={"value": "+41446681800"})
    assert run.status_code == 201
    assert run.json()["data"]["detected"] == "phone"
    assert run.json()["data"]["runs"][0]["status"] == "ok"
    case = api.get("/api/cases/1").json()["data"]
    assert len(case["lookups"]) == 1
    assert case["lookups"][0]["query"] == "+41446681800"
    assert case["lookups"][0]["runs"][0]["module_id"] == "phone"
    skipped = api.post("/api/cases/1/lookup", json={"value": "+41446681800", "modules": ["email"]})
    assert skipped.status_code == 400


def test_home_shell(tmp_path):
    response = client(tmp_path).get("/")
    assert response.status_code == 200
    assert "Fennec" in response.text
    assert "/static/favicon.svg" in response.text
    assert 'id="tool-list"' in response.text
    assert 'id="smart-input"' in response.text
    assert "/static/app.js" in response.text


def test_select_sites_keeps_a_small_set():
    from types import SimpleNamespace

    from app.modules.email import select_sites

    sites = [SimpleNamespace(__name__=name) for name in ("github", "pornhub", "twitter")]
    names = {item.__name__ for item in select_sites(sites)}
    assert names == {"github", "twitter"}
