import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_-]{2,22}$")
SPEC = ModuleSpec(
    id="reddit",
    title="Reddit",
    milestone="later",
    summary="One Reddit about.json lookup.",
    input_label="Reddit username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://www.reddit.com/user/{login}/about.json",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return (response.json() or {}).get("data") or {}


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip().lstrip("u/")
    if login.startswith("/"):
        login = login[1:]
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a Reddit username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Reddit lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No Reddit user with that name.")
    findings = [
        Finding("username", str(data.get("name") or login), "reddit", "high", f"https://www.reddit.com/user/{login}"),
    ]
    sub = data.get("subreddit") or {}
    if sub.get("title"):
        findings.append(Finding("name", str(sub["title"]), "reddit", "medium", "Profile title"))
    if sub.get("public_description"):
        findings.append(Finding("note", str(sub["public_description"])[:400], "reddit", "low", "Public description"))
    if data.get("total_karma") is not None:
        findings.append(Finding("note", f"karma {data['total_karma']}", "reddit", "low", "Total karma"))
    return ModuleResult(status="ok", findings=findings)
