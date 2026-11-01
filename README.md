# Fennec

Local open-source OSINT workbench. Cases and findings live in SQLite. Every action is a JSON API, and the page in the browser calls that same API.

The milestone plan is in [Fennec_Plan.md](Fennec_Plan.md).

## Status

Workbench shell, cases, and the phone module (`phonenumbers`) are in place. Username, email, domain, and file metadata are registered and return `module_unavailable` until their milestones.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

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

Pinned in `requirements.txt`: FastAPI 0.162, Uvicorn 0.54, Jinja2 3.1.6, phonenumbers 9.0.42, pytest 9.2, httpx 0.28.1. Later milestones add Maigret, Holehe, dnspython, and whoisdomain (RDAP first). `python-whois` is not the default because gTLD WHOIS has been retired.

Lawful use only. Phone results are numbering-plan metadata, not a subscriber lookup.
