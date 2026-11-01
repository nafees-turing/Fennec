import re
from urllib.parse import quote

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="wikipedia",
    title="Wikipedia",
    milestone="later",
    summary="One Wikipedia REST summary for a person or topic.",
    input_label="Name or title",
    placeholder="Ada Lovelace",
    available=True,
    network=True,
    category="basic",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_summary(title: str) -> dict:
    import httpx

    slug = quote(title.replace(" ", "_"))
    response = httpx.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    title = re.sub(r"\s+", " ", raw).strip()
    if len(title) < 2 or len(title) > 80:
        return ModuleResult(status="failed", error="Enter a Wikipedia title or person name.")
    scanner = scanner or fetch_summary
    try:
        data = scanner(title)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Wikipedia failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No Wikipedia summary for that title.")
    page = ((data.get("content_urls") or {}).get("desktop") or {}).get("page") or ""
    findings = [
        Finding("name", str(data.get("title") or title), "wikipedia", "medium", data.get("description") or "Summary"),
    ]
    if page:
        findings.append(Finding("url", page, "wikipedia", "high", "Article"))
    if data.get("extract"):
        findings.append(Finding("note", str(data["extract"])[:500], "wikipedia", "medium", "Lead extract"))
    return ModuleResult(status="ok", findings=findings)
