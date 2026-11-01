import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_-]{3,25}$")
SPEC = ModuleSpec(
    id="chess",
    title="Chess.com",
    milestone="later",
    summary="One Chess.com public player profile.",
    input_label="Chess.com username",
    placeholder="hikaru",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_player(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://api.chess.com/pub/player/{login}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip().lstrip("@")
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a Chess.com username.")
    scanner = scanner or fetch_player
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Chess.com failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No Chess.com player with that name.")
    findings = [
        Finding("username", str(data.get("username") or login), "chess.com", "high", str(data.get("url") or "")),
    ]
    if data.get("name"):
        findings.append(Finding("name", str(data["name"]), "chess.com", "medium", "Public name"))
    if data.get("location"):
        findings.append(Finding("address", str(data["location"]), "chess.com", "low", "Profile location"))
    if data.get("country"):
        findings.append(Finding("country", str(data["country"]).rsplit("/", 1)[-1], "chess.com", "low", "Country code URL"))
    if data.get("title"):
        findings.append(Finding("note", str(data["title"]), "chess.com", "low", "Title"))
    return ModuleResult(status="ok", findings=findings)
