# Fennec

Local open-source OSINT workbench. Cases and findings live in SQLite. Every action is a JSON API, and the page in the browser calls that same API.

The milestone plan is in [Fennec_Plan.md](Fennec_Plan.md).

## Status

Cases, phone, email (Holehe), and domain (dnspython + whoisdomain) are live. Username and file metadata stay registered and return `module_unavailable` until their milestones. An email run contacts many sites and can take about a minute. Domain looks up public DNS and RDAP/WHOIS. pytest injects fakes and does not hit the network.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Use `python -m uvicorn` from that venv. A system `uvicorn` on PATH will miss Holehe’s `trio` dependency.

Open http://127.0.0.1:8000. The database file is `data/fennec.db`.

## API

Responses are either `{"data": ...}` or `{"error": {"code": "...", "message": "..."}}`.

| Method | Path | Role |
|--------|------|------|
| GET | `/api/health` | Process and storage check |
| GET | `/api/modules` | Registered modules and whether each one can run |
| GET | `/api/cases` | List cases |
| POST | `/api/cases` | `{"name": "...", "notes": ""}` |
| GET | `/api/cases/{id}` | Case, runs, and findings |
| POST | `/api/cases/{id}/runs` | `{"module": "phone", "value": "+14155552671"}` |

## Test

```bash
pytest
```

## Libraries

Pinned in `requirements.txt`: FastAPI 0.162, Uvicorn 0.54, Jinja2 3.1.6, phonenumbers 9.0.42, holehe 1.61, dnspython 2.9.1, whoisdomain 2.20260806.3, pytest 9.2, httpx 0.28.1. Later milestones add Maigret and ExifTool. `python-whois` is not the default because gTLD WHOIS has been retired.

Lawful use only. Phone results are numbering-plan metadata, not a subscriber lookup.
