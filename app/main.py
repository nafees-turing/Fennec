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

from app import correlate, db, detect as detect_mod, keep
from app.people import edits as profile_edits
from app.people import enrich as profile_enrich
from app.people import export as profile_export
from app.people import profiles as profiles_mod
from app.people import suggest as profile_suggest
from app.modules.base import ModuleResult
from app.modules.registry import COMPANY_MODULES, DEFAULT_MODULES, execute, get_module, list_modules
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
        available = [item.id for item in list_modules() if item.available]
        return ok(
            {
                "default_modules": load_defaults(),
                "personal_defaults": list(DEFAULT_MODULES),
                "presets": {
                    "personal": list(DEFAULT_MODULES),
                    "company": list(COMPANY_MODULES),
                    "advanced": available,
                },
            }
        )

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
        pending_raw = db.get_pending(app.state.db_path, case_id)
        case["pending"] = json.loads(pending_raw) if pending_raw else None
        profile_run_ids = {int(run["id"]) for run in case["runs"] if run.get("in_profile")}
        profile_findings = [row for row in case["findings"] if row.get("run_id") in profile_run_ids]
        profile_lookups = [
            lookup
            for lookup in case["lookups"]
            if any(run.get("in_profile") for run in lookup.get("runs") or [])
        ]
        case["profiles"] = profiles_mod.build(
            profile_findings,
            profile_lookups,
            unions=db.list_unions(app.state.db_path, case_id),
        )
        case["profiles"] = profile_edits.apply_edits(
            case["profiles"],
            db.list_edits(app.state.db_path, case_id),
        )
        for profile in case["profiles"]:
            profile["actions"] = profile_enrich.available_actions(profile)
        for lookup in case["lookups"]:
            query = str(lookup.get("query") or "")
            attached = profile_suggest.attached_profile(query, case["profiles"])
            lookup["attached_id"] = attached["id"] if attached else None
            lookup["candidates"] = profile_suggest.candidates(query, case["profiles"])
        return case

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: int) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        return ok(case)

    @app.post("/api/cases/{case_id}/profiles/{profile_id}/attach")
    async def attach_lookup(case_id: int, profile_id: int, request: Request) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        profile = next((item for item in case["profiles"] if item["id"] == profile_id), None)
        if profile is None:
            return fail("profile_not_found", "No profile with that id.", 404)
        body = await request.json()
        lookup_id = str(body.get("lookup_id") or "")
        lookup = next((item for item in case["lookups"] if item["id"] == lookup_id), None)
        if lookup is None:
            return fail("lookup_not_found", "No search with that id.", 404)
        query_keys = profiles_mod._from_query(str(lookup.get("query") or ""))
        targets = profiles_mod.anchor_keys(profile)
        if not query_keys or not targets:
            return fail("cannot_attach", "Need a person identifier on both the search and the profile.", 400)
        for left in query_keys:
            db.add_union(app.state.db_path, case_id, left, targets[0])
        updated = load_case(case_id)
        return ok({"profiles": updated["profiles"] if updated else []})

    @app.put("/api/cases/{case_id}/profiles/{profile_id}")
    async def edit_profile(case_id: int, profile_id: int, request: Request) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        profile = next((item for item in case["profiles"] if item["id"] == profile_id), None)
        if profile is None:
            return fail("profile_not_found", "No profile with that id.", 404)
        keys = profiles_mod.anchor_keys(profile)
        if not keys:
            return fail("cannot_edit", "This profile has no identity key to store notes on.", 400)
        body = await request.json()
        saved = db.upsert_edit(app.state.db_path, case_id, keys[0], body)
        updated = load_case(case_id)
        return ok({"edit": saved, "profiles": updated["profiles"] if updated else []})

    @app.post("/api/cases/{case_id}/profiles/{profile_id}/enrich")
    async def enrich_profile(case_id: int, profile_id: int, request: Request) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        profile = next((item for item in case["profiles"] if item["id"] == profile_id), None)
        if profile is None:
            return fail("profile_not_found", "No profile with that id.", 404)
        body = await request.json()
        set_id = str(body.get("set") or "")
        spec = profile_enrich.SETS.get(set_id)
        if spec is None:
            return fail("unknown_set", "Use social, email, name, or phone.", 400)
        value = str(body.get("value") or profile_enrich.seed_value(profile, spec["seed"]) or "").strip()
        if not value:
            return fail("no_seed", f"This profile has no {spec['seed']} to search with.", 400)
        lookup_id = uuid.uuid4().hex
        ran = []
        for module_id in spec["modules"]:
            preview, error = await preview_module(app, module_id, value)
            if error or not preview or not preview.get("findings"):
                continue
            db.add_run(
                app.state.db_path,
                case_id,
                module_id,
                str(preview.get("status") or "ok"),
                value,
                preview.get("error"),
                list(preview.get("findings") or []),
                lookup_id=lookup_id,
                in_profile=True,
            )
            ran.append(module_id)
        query_keys = profiles_mod._from_query(value)
        targets = profiles_mod.anchor_keys(profile)
        if query_keys and targets:
            for left in query_keys:
                db.add_union(app.state.db_path, case_id, left, targets[0])
        updated = load_case(case_id)
        return ok({"ran": ran, "value": value, "profiles": updated["profiles"] if updated else []})

    @app.get("/api/cases/{case_id}/profiles/{profile_id}/export.html", response_class=HTMLResponse)
    def export_profile_html(case_id: int, profile_id: int):
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        profile = next((item for item in case["profiles"] if item["id"] == profile_id), None)
        if profile is None:
            return fail("profile_not_found", "No profile with that id.", 404)
        return HTMLResponse(profile_export.render_html(profile, case.get("name") or ""))

    @app.get("/api/cases/{case_id}/profiles/{profile_id}/export.pdf")
    def export_profile_pdf(case_id: int, profile_id: int):
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        profile = next((item for item in case["profiles"] if item["id"] == profile_id), None)
        if profile is None:
            return fail("profile_not_found", "No profile with that id.", 404)
        payload = profile_export.render_pdf(profile, case.get("name") or "")
        return Response(
            content=payload,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="fennec-profile-{profile_id}.pdf"'},
        )

    @app.delete("/api/cases/{case_id}/profiles/{profile_id}")
    def delete_profile(case_id: int, profile_id: int) -> JSONResponse:
        case = load_case(case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        profile = next((item for item in case["profiles"] if item["id"] == profile_id), None)
        if profile is None:
            return fail("profile_not_found", "No profile with that id.", 404)
        removed = db.delete_findings(app.state.db_path, case_id, profile.get("finding_ids") or [])
        return ok({"removed": removed, "profile_id": profile_id})

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
            preview, error = await preview_module(app, item["module"], item["value"])
            if error:
                continue
            preview["match_label"] = item["label"]
            if preview["status"] == "ok" and preview["findings"]:
                runs.append(preview)
        pending = {
            "id": lookup_id,
            "query": value,
            "detected": classified["detected"],
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pending": True,
            "runs": runs,
        }
        db.set_pending(app.state.db_path, case_id, json.dumps(pending))
        return ok(pending, 201)

    @app.post("/api/cases/{case_id}/commit")
    async def commit_lookup(case_id: int, request: Request) -> JSONResponse:
        if db.get_case(app.state.db_path, case_id) is None:
            return fail("case_not_found", "No case with that id.", 404)
        raw = db.get_pending(app.state.db_path, case_id)
        if not raw:
            return fail("no_pending", "There is no unsaved search to keep.", 400)
        pending = json.loads(raw)
        body = await request.json()
        action = str(body.get("action") or "search")
        if action not in {"search", "profile", "attach"}:
            return fail("invalid_action", "Use search, profile, or attach.", 400)
        lookup_id = str(pending.get("id") or uuid.uuid4().hex)
        in_profile = action in {"profile", "attach"}
        for run in pending.get("runs") or []:
            db.add_run(
                app.state.db_path,
                case_id,
                str(run.get("module_id") or ""),
                str(run.get("status") or "ok"),
                str(run.get("input_value") or pending.get("query") or ""),
                run.get("error"),
                list(run.get("findings") or []),
                lookup_id=lookup_id,
                in_profile=in_profile,
            )
        if action == "attach":
            profile_id = int(body.get("profile_id") or 0)
            case = load_case(case_id)
            profile = next((item for item in (case or {}).get("profiles") or [] if item["id"] == profile_id), None)
            if profile is None:
                return fail("profile_not_found", "No profile with that id.", 404)
            query_keys = profiles_mod._from_query(str(pending.get("query") or ""))
            targets = profiles_mod.anchor_keys(profile)
            if query_keys and targets:
                for left in query_keys:
                    db.add_union(app.state.db_path, case_id, left, targets[0])
            db.mark_runs_in_profile(app.state.db_path, case_id, lookup_id)
        if action == "profile":
            title = str(body.get("title") or "").strip()
            case = load_case(case_id)
            query_keys = profiles_mod._from_query(str(pending.get("query") or ""))
            if title and query_keys:
                db.upsert_edit(app.state.db_path, case_id, query_keys[0], {"title": title})
        db.clear_pending(app.state.db_path, case_id)
        return ok(load_case(case_id))

    @app.delete("/api/cases/{case_id}/pending")
    def discard_pending(case_id: int) -> JSONResponse:
        db.clear_pending(app.state.db_path, case_id)
        return ok({"discarded": True})

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


async def preview_module(app: FastAPI, module_id: str, value: str):
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
    findings = keep.filter_findings([item.as_dict() for item in result.findings])
    return {
        "module_id": module_id,
        "status": result.status,
        "input_value": value,
        "error": result.error,
        "findings": findings,
    }, None


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
        keep.filter_findings([item.as_dict() for item in result.findings]),
        lookup_id=lookup_id,
    )
    return run, None




app = create_app()
