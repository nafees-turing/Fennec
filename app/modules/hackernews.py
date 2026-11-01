import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_-]{2,39}$")
SPEC = ModuleSpec(
    id="hackernews",
    title="Hacker News",
    milestone="later",
    summary="One Firebase HN user lookup.",
    input_label="HN username",
    placeholder="pg",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://hacker-news.firebaseio.com/v0/user/{login}.json",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    data = response.json()
    return data or {}


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip().lstrip("@")
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a Hacker News username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"HN lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No HN user with that name.")
    findings = [
        Finding("username", str(data.get("id") or login), "hackernews", "high", f"https://news.ycombinator.com/user?id={login}"),
    ]
    if data.get("karma") is not None:
        findings.append(Finding("note", f"karma {data['karma']}", "hackernews", "low", "Public karma"))
    if data.get("about"):
        findings.append(Finding("note", str(data["about"])[:400], "hackernews", "medium", "About text"))
    return ModuleResult(status="ok", findings=findings)
