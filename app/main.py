from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Fennec")

TEMPLATES = Path(__file__).resolve().parent / "web"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "Fennec", "milestone": "M0"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (TEMPLATES / "index.html").read_text(encoding="utf-8")
