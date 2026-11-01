# Fennec

Local open-source OSINT workbench. One case file on your machine, modules added one milestone at a time.

The build plan, milestone tests, and tool list are in [Fennec_Plan.md](Fennec_Plan.md).

## Status

**M0 — shell.** Health check and a home page. Username, email, domain, and metadata modules are planned and not installed yet.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000

## Test

```bash
pytest
```

M0 does not call the network or any OSINT tool.

## Use

Lawful use only: your own data, authorized work, journalism, and research. Results stay in this local process. See the plan for the full rule.
