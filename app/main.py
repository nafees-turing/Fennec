import asyncio
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from app import pdf as pdf_export
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app import correlate, db
from app.modules.base import ModuleResult
from app.modules.registry import execute, get_module, list_modules
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

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return (WEB / "index.html").read_text(encoding="utf-8")

    @app.get("/api/health")
    def health() -> JSONResponse:
        return ok({"status": "ok", "app": "Fennec", "storage": "sqlite", "version": app.version})

    @app.get("/api/modules")
    def modules() -> JSONResponse:
        return ok([item.as_dict() for item in list_modules()])

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
        key = f"{module_id}:{value.lower()}"
        if spec.network:
            blocked = app.state.network.begin(key)
            if blocked:
                return fail("network_limited", blocked, 429)
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
        )
        return ok(run, 201)

    return app


app = create_app()
