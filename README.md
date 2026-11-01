# Fennec

Local open-source OSINT workbench. Cases and findings live in SQLite. Every action is a JSON API, and the page in the browser calls that same API.

The milestone plan is in [Fennec_Plan.md](Fennec_Plan.md).

## Status

Live modules: phone, email, username, domain, company (Wikidata), geoip (local mmdb), file metadata, correlation, JSON/HTML/PDF export, Docker image.

Network modules stay small and slow: about 20 Holehe sites, eight username profile URLs, one domain RDAP/WHOIS plus DNS, at most two Wikimedia requests for a company. One network scan at a time, then a cooldown. Phone, metadata, geoip, and correlation never leave the machine. Set `FENNEC_HOLEHE_SITES=all` only if you want the full Holehe list. Full Maigret is still out.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Use `python -m uvicorn` from that venv. A system `uvicorn` on PATH will miss Holehe’s `trio` dependency.

Open http://127.0.0.1:8000. The database file is `data/fennec.db`.

GeoIP: put `GeoLite2-Country.mmdb` (or City) in `data/` or set `FENNEC_GEOLITE`. Fennec does not download that file.

Docker:

```bash
docker compose up --build
```

The compose file mounts `./data` so SQLite and the GeoIP database persist.

## API

Responses are either `{"data": ...}` or `{"error": {"code": "...", "message": "..."}}`.

| Method | Path | Role |
|--------|------|------|
| GET | `/api/health` | Process and storage check |
| GET | `/api/modules` | Registered modules and whether each one can run |
| GET | `/api/cases` | List cases |
| POST | `/api/cases` | `{"name": "...", "notes": ""}` |
| GET | `/api/cases/{id}` | Case, runs, findings, and links |
| POST | `/api/cases/{id}/runs` | `{"module": "phone", "value": "+14155552671"}` |
| GET | `/api/cases/{id}/export` | JSON dossier |
| GET | `/api/cases/{id}/export.html` | HTML dossier |
| GET | `/api/cases/{id}/export.pdf` | PDF dossier |

## Test

```bash
pytest
```

## Libraries

Pinned in `requirements.txt`: FastAPI 0.162, Uvicorn 0.54, Jinja2 3.1.6, phonenumbers 9.0.42, holehe 1.61, dnspython 2.9.1, whoisdomain 2.20260806.3, pytest 9.2, httpx 0.28.1. Later milestones add Maigret and ExifTool. `python-whois` is not the default because gTLD WHOIS has been retired.

Lawful use only. Phone results are numbering-plan metadata, not a subscriber lookup.
