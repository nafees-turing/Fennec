import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app import pdf as pdf_export
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import correlate, db, detect as detect_mod, profiles as profiles_mod
from app.modules.base import ModuleResult
from app.modules.registry import DEFAULT_MODULES, execute, get_module, list_modules
from app.netguard import NetworkGuard

WEB = Path(__file__).resolve().parent / "web"
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
MAX_UPLOAD = 20 * 1024 * 1024


def ok(data: object, status_code: int = 200) -> JSONResponse:
    return JSONResponse({"data": data}, status_code=status_code)


def fail(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status_code)


def create_app(
    db_path: Path | None = None,
    network_cooldown: float = 45.0,
    run_timeout: float = 90.0,
) -> FastAPI:
    app = FastAPI(title="Fennec", version="0.1.0")
    app.state.db_path = db_path or Path("data") / "fennec.db"
    app.state.network = NetworkGuard(cooldown=network_cooldown)
    app.state.run_timeout = run_timeout
    db.init_db(app.state.db_path)
    app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
    templates = Jinja2Templates(directory=str(WEB))

    def spa() -> str:
        return (WEB / "index.html").read_text(encoding="utf-8")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return spa()

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def case_page(case_id: int) -> str:
        return spa()

    @app.get("/cases/{case_id}/profiles/{profile_id}", response_class=HTMLResponse)
    def profile_page(case_id: int, profile_id: int) -> str:
        return spa()

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page() -> str:
        return spa()

    @app.get("/api/health")
    def health() -> JSONResponse:
        return ok({"status": "ok", "app": "Fennec", "storage": "sqlite", "version": app.version})

    @app.get("/api/modules")
    def modules() -> JSONResponse:
        return ok([item.as_dict() for item in list_modules()])

    @app.get("/api/detect")
    def detect(q: str = "") -> JSONResponse:
        return ok(detect_mod.classify(q))

    def load_defaults() -> list[str]:
        raw = db.get_setting(app.state.db_path, "default_modules")
        if not raw:
            return list(DEFAULT_MODULES)
        try:
            values = json.loads(raw)
        except json.JSONDecodeError:
            return list(DEFAULT_MODULES)
        if not isinstance(values, list):
            return list(DEFAULT_MODULES)
        known = {item.id for item in list_modules()}
        return [str(item) for item in values if str(item) in known]

    @app.get("/api/settings")
    def get_settings() -> JSONResponse:
        return ok({"default_modules": load_defaults(), "personal_defaults": list(DEFAULT_MODULES)})

    @app.put("/api/settings")
    async def put_settings(request: Request) -> JSONResponse:
        body = await request.json()
        values = body.get("default_modules")
        if not isinstance(values, list):
            return fail("invalid_settings", "default_modules must be a list of tool ids.", 400)
        known = {item.id for item in list_modules()}
        chosen = [str(item) for item in values if str(item) in known]
        db.set_setting(app.state.db_path, "default_modules", json.dumps(chosen))
        return ok({"default_modules": chosen, "personal_defaults": list(DEFAULT_MODULES)})

    @app.get("/api/cases")
    def cases() -> JSONResponse:
        return ok(db.list_cases(app.state.db_path))

    @app.post("/api/cases")
    async def create_case(request: Request) -> JSONResponse:
        body = await request.json()
        name = str(body.get("name", "")).strip()
        notes = str(body.get("notes", "")).strip()
        if not name:
            return fail("invalid_case", "Case name is required.", 400)
        created = db.create_case(app.state.db_path, name, notes)
        return ok(created, 201)

    def load_case(case_id: int) -> dict | None:
        case = db.get_case(app.state.db_path, case_id)
        if case is None:
            return None
        case["runs"] = db.list_runs(app.state.db_path, case_id)
        case["findings"] = db.list_findings(app.state.db_path, case_id)
        case["links"] = correlate.links(case["findings"])
        case["lookups"] = group_lookups(case["runs"], case["findings"])
        case["profiles"] = profiles_mod.build(case["findings"], case["lookups"])
        return case

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: int) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        return ok(case)

    @app.get("/api/cases/{case_id}/export")
    def export_case(case_id: int) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        case["exported_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return ok(case)

    @app.get("/api/cases/{case_id}/export.html", response_class=HTMLResponse)
    def export_html(request: Request, case_id: int):
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        return templates.TemplateResponse(
            request,
            "dossier.html",
            {
                "case": case,
                "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )

    @app.get("/api/cases/{case_id}/export.pdf")
    def export_pdf(case_id: int):
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        payload = pdf_export.render(case)
        filename = f"fennec-case-{case_id}.pdf"
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.post("/api/cases/{case_id}/runs")
    async def create_run(case_id: int, request: Request) -> JSONResponse:
        if db.get_case(app.state.db_path, case_id) is None:
            return fail("case_not_found", "No case with that id.", 404)
        content_type = request.headers.get("content-type", "")
        if content_type.startswith("multipart/form-data"):
            form = await request.form()
            module_id = str(form.get("module") or "").strip()
            upload = form.get("file")
            if upload is None or not getattr(upload, "filename", None):
                return fail("invalid_input", "A file is required.", 400)
            data = await upload.read()
            if len(data) > MAX_UPLOAD:
                return fail("file_too_large", "File is over 20 MB.", 400)
            name = SAFE_NAME.sub("_", Path(str(upload.filename)).name) or "upload.bin"
            folder = app.state.db_path.parent / "files" / str(case_id)
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / name
            path.write_bytes(data)
            value = str(path)
        else:
            body = await request.json()
            module_id = str(body.get("module", "")).strip()
            value = str(body.get("value", "")).strip()
        spec = get_module(module_id)
        if spec is None:
            return fail("unknown_module", "That module is not registered.", 404)
        if not value:
            return fail("invalid_input", "A value is required.", 400)
        if not spec.available:
            return fail("module_unavailable", spec.reason, 409)
        run, error = await run_module(app, case_id, module_id, value, lookup_id=uuid.uuid4().hex)
        if error:
            return fail(error["code"], error["message"], error["status"])
        return ok(run, 201)

    @app.post("/api/cases/{case_id}/lookup")
    async def smart_lookup(case_id: int, request: Request) -> JSONResponse:
        if db.get_case(app.state.db_path, case_id) is None:
            return fail("case_not_found", "No case with that id.", 404)
        body = await request.json()
        value = str(body.get("value", "")).strip()
        if not value:
            return fail("invalid_input", "A value is required.", 400)
        classified = detect_mod.classify(value)
        if not classified["matches"]:
            return fail("unrecognized", "Could not tell if that is an email, phone, domain, IP, or handle.", 400)
        wanted = body.get("modules")
        if isinstance(wanted, list):
            allowed = {str(item) for item in wanted}
            classified["matches"] = [item for item in classified["matches"] if item["module"] in allowed]
            if not classified["matches"]:
                return fail("no_tools", "No selected tools apply to that value. Turn on tags or change Settings.", 400)
        lookup_id = uuid.uuid4().hex
        runs = []
        for item in classified["matches"]:
            run, error = await run_module(app, case_id, item["module"], item["value"], lookup_id=lookup_id)
            if error:
                runs.append(
                    {
                        "module_id": item["module"],
                        "status": "skipped",
                        "input_value": item["value"],
                        "error": error["message"],
                        "match_label": item["label"],
                        "findings": [],
                    }
                )
                continue
            run["match_label"] = item["label"]
            runs.append(run)
        return ok({"detected": classified["detected"], "matches": classified["matches"], "runs": runs}, 201)

    return app


def group_lookups(runs: list[dict], findings: list[dict]) -> list[dict]:
    by_run: dict[int, list[dict]] = {}
    for row in findings:
        by_run.setdefault(row["run_id"], []).append(row)
    groups: dict[str, dict] = {}
    order: list[str] = []
    for run in runs:
        lid = run.get("lookup_id") or f"run-{run['id']}"
        if lid not in groups:
            groups[lid] = {
                "id": lid,
                "query": run.get("input_value") or "",
                "created_at": run.get("created_at") or "",
                "runs": [],
            }
            order.append(lid)
        item = dict(run)
        item["findings"] = by_run.get(run["id"], [])
        groups[lid]["runs"].append(item)
    return [groups[key] for key in order]


async def run_module(app: FastAPI, case_id: int, module_id: str, value: str, lookup_id: str | None = None):
    spec = get_module(module_id)
    if spec is None or not spec.available:
        return None, {"code": "module_unavailable", "message": "That module cannot run.", "status": 409}
    key = f"{module_id}:{value.lower()}"
    if spec.network:
        blocked = app.state.network.begin(key)
        if blocked:
            return None, {"code": "network_limited", "message": blocked, "status": 429}
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(execute, module_id, value),
            timeout=app.state.run_timeout,
        )
    except TimeoutError:
        result = ModuleResult(status="failed", error="Timed out before the module finished.")
    finally:
        if spec.network:
            app.state.network.end(key)
    run = db.add_run(
        app.state.db_path,
        case_id,
        module_id,
        result.status,
        value,
        result.error,
        [item.as_dict() for item in result.findings],
        lookup_id=lookup_id,
    )
    return run, None




app = create_app()
