import asyncio
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.modules.registry import execute, get_module, list_modules

WEB = Path(__file__).resolve().parent / "web"


def ok(data: object, status_code: int = 200) -> JSONResponse:
    return JSONResponse({"data": data}, status_code=status_code)


def fail(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status_code)


def create_app(db_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="Fennec", version="0.1.0")
    app.state.db_path = db_path or Path("data") / "fennec.db"
    db.init_db(app.state.db_path)
    app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")

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

    @app.get("/api/cases/{case_id}")
    def case_detail(case_id: int) -> JSONResponse:
        case = db.get_case(app.state.db_path, case_id)
        if case is None:
            return fail("case_not_found", "No case with that id.", 404)
        case["runs"] = db.list_runs(app.state.db_path, case_id)
        case["findings"] = db.list_findings(app.state.db_path, case_id)
        return ok(case)

    @app.post("/api/cases/{case_id}/runs")
    async def create_run(case_id: int, request: Request) -> JSONResponse:
        if db.get_case(app.state.db_path, case_id) is None:
            return fail("case_not_found", "No case with that id.", 404)
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
        result = await asyncio.to_thread(execute, module_id, value)
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
