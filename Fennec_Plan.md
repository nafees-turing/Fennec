# Fennec

**A local, open-source OSINT workbench**

Fennec is a self-hosted platform that wraps well-known open-source OSINT tools behind one local web app. Investigations stay on your machine. The core path uses public methods and open-source projects only. Paid APIs are out of the default build.

Each milestone below is a separate slice of work. Finish it, test it, then start the next one. Later milestones must not block earlier ones from running.

---

## What “open source OSINT” means here

Fennec follows the same shape as public projects such as SpiderFoot (modular scans and correlation), Maigret and Sherlock (username search), Holehe (email registration checks), theHarvester (domain harvest), and recon-style DNS/WHOIS lookups.

Rules for every milestone:

- Prefer tools and data sources whose code and methods are public.
- Call those tools through a thin adapter so the UI does not depend on one CLI.
- Do not require API keys for the default path.
- Store cases, raw tool output, and normalized results locally (SQLite plus files).
- Ship a test that proves the milestone works without hitting the live internet when a fixture or fake adapter can stand in.

Lawful use only: your own accounts, authorized work, journalism, and research. Respect site terms, rate limits, and robots.txt. No stalking, harassment, or unauthorized access.

---

## Product shape

One local web app:

1. Create a **case**.
2. Run a **module** (username, email, domain, phone, or file metadata).
3. See **normalized findings** plus the raw tool output.
4. Export a **dossier** (JSON, then HTML).
5. Later, link findings into a simple graph.

Recommended stack, fixed for the first milestones so we do not rebuild the shell twice:

| Layer | Choice | Why |
|-------|--------|-----|
| API | FastAPI JSON envelope | `{"data": ...}` or `{"error": {"code", "message"}}`. The UI uses only this API |
| UI | Server-rendered pages (Jinja) + a little HTMX | One process, no separate frontend repo yet |
| Store | SQLite | Cases and findings without another service |
| Tools | Subprocess or library adapters | Maigret, Holehe, dnspython, whoisdomain, phonenumbers, ExifTool |
| Tests | pytest + adapter fakes | Each phase can pass offline |

SpiderFoot stays optional and out of the core. It is a full framework, not a library we need on day one.

---

## Architecture

```
Fennec/
├── app/
│   ├── main.py                 # FastAPI app
│   ├── db.py                   # SQLite
│   ├── models.py               # Case, Run, Finding
│   ├── adapters/
│   │   ├── base.py             # Adapter protocol + fake adapter
│   │   ├── username.py         # Maigret
│   │   ├── email.py            # Holehe
│   │   ├── domain.py           # WHOIS + DNS
│   │   └── metadata.py         # ExifTool
│   └── web/                    # Templates for the local UI
├── tests/                      # One test module per milestone
├── data/                       # Local DB and case files (gitignored)
├── Fennec_Plan.md
├── README.md
└── requirements.txt
```

A **finding** is the shared record every module writes:

- `kind`: username, email, domain, phone, url, ip, file
- `value`
- `source`: which tool
- `confidence`: low / medium / high
- `evidence`: short note or raw snippet
- `case_id` and `run_id`

---

## Milestones

Work top to bottom. Each milestone has a done test. Do not start the next feature work until that test is green.

### M0 — Shell

Empty app that runs locally.

- `GET /health` returns ok.
- Home page names the app Fennec and lists modules as not installed yet.
- README explains setup and the lawful-use rule.
- pytest covers `/health`.

**Test:** `pytest` passes with no network and no OSINT tools installed.

### M1 — Cases

- Create, list, and open a case (name, notes, created time).
- SQLite file under `data/`.
- A case page with an empty findings list.

**Test:** create a case through the API or test client, read it back, restart is not required for the assertion (use a temp database).

### M2 — Username

- Adapter around Maigret for one username.
- If Maigret is missing, the UI says so and the test uses a fake adapter.
- Save each hit as a finding on the case.
- Show found profile URLs on the case page.

**Test:** fake adapter returns two sites; both land in the case. Optional marked test runs Maigret only when the binary or package is present.

### M3 — Email

- Adapter around Holehe for one email. Real scans call 120+ sites from this machine.
- Tests inject a fake scanner so pytest stays offline.
- Store the email, each registered site as `account`, and rate-limited sites as `rate_limit`. Negative results are dropped so the case is readable.

**Test:** fake Holehe-style results persist and show on the case. A bad address fails the run.

### M4 — Domain

- DNS (A, AAAA, MX, NS, TXT) via dnspython.
- Registration via whoisdomain, RDAP first, classic WHOIS if RDAP is empty.
- Tests inject fake DNS and WHOIS so pytest stays offline.
- No theHarvester in this milestone.

**Test:** fixture in, findings out, no live DNS. A junk host fails the run.

### M5 — Phone

Library: [`phonenumbers`](https://github.com/daviddrysdale/python-phonenumbers), the Python port of Google's [libphonenumber](https://github.com/google/libphonenumber). Apache-2.0. Current PyPI line is 9.x. `pip install phonenumbers`. No API key and no network call. Metadata ships inside the package.

Input is a number in international form (`+…`). The module records only what the numbering plan publishes:

- valid and possible
- international and national format
- country calling code
- region description (`geocoder.description_for_number`)
- time zones for that numbering range
- original carrier for the assigned prefix (`carrier.name_for_number`), when the metadata has one

Limits to show in the UI, because the library's own docs say this:

- Carrier is the original prefix owner, not the carrier after number portability.
- Region is the area-code or country label from the numbering plan. It is not the person's location.
- This does not identify the subscriber.

**Test:** parse a fixed example such as `+41446681800` with the real library (offline) and store region, country code, and formatted value as findings. A second case uses an impossible string and stores a failed run, not a crash.

### M6 — Metadata

- Upload a file into the case.
- Run ExifTool when installed.
- Offline test parses a checked-in fixture of ExifTool JSON (no real GPS of a private person; use a synthetic fixture).

**Test:** fixture metadata becomes findings (software, timestamp). GPS only if the fixture contains it.

### M7 — Dossier export

- `GET` a case as JSON.
- HTML report rendered from the same findings.
- Export does not call external tools.

**Test:** case with mixed findings exports stable JSON keys and HTML that includes each value.

### M8 — Correlation

- Link findings that share a username, email, domain, or phone number.
- Simple list of links first. Graph view after the list is tested.
- No new collectors in this milestone.

**Test:** two findings that share a domain produce one link. Unrelated findings produce none.

### M9 — Run history and safety rails

- Each module run stores status, start, finish, and tool version or “fake”.
- Timeouts and non-zero exits become a failed run, not a crash.
- Basic rate limit: one active run per case.

**Test:** a hanging fake adapter hits the timeout and the case stays readable.

### Later, only after M0–M9

- Subdomain helper (subfinder or theHarvester) behind the same adapter interface.
- Optional offline GeoIP using a locally downloaded MaxMind or DB-IP database.
- PDF export.
- Docker image.
- Dark case-file theme.

Breach APIs that need a paid key (including Have I Been Pwned) stay optional plugins and are not part of the default milestones.

---

## How to complete a milestone

1. Branch or a small commit named `mN-short-name`.
2. Implement only that milestone’s files.
3. Add or extend the pytest for that milestone.
4. Run `pytest`.
5. Smoke-test the UI path in a browser when the milestone changes a page.
6. Merge, then pull the next milestone from this list.

---

## Open-source tools (default set)

| Tool | Milestone | Role |
|------|-----------|------|
| Maigret | M2 | Username profiles |
| Holehe | M3 | Email → sites |
| dnspython | M4 | DNS |
| whoisdomain | M4 | WHOIS, RDAP first. gTLD WHOIS was sunset, so python-whois is not the default |
| phonenumbers | M5 | Phone number metadata from the public numbering plan |
| ExifTool | M6 | File metadata |

Sherlock overlaps Maigret. Use Maigret only unless a later note says otherwise.

---

## Non-goals

- Cloud accounts, telemetry, or phone-home.
- Scrapers written from scratch when a maintained open-source tool already does the job.
- Hidden collection, credential theft, or anything aimed at breaking into accounts.
- A multi-user product. One operator, one machine.
