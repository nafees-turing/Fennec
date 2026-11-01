import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9._-]{2,39}$")
SPEC = ModuleSpec(
    id="gitlab",
    title="GitLab",
    milestone="later",
    summary="One GitLab.com user API lookup.",
    input_label="GitLab username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        "https://gitlab.com/api/v4/users",
        params={"username": login},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    rows = response.json()
    return rows[0] if rows else {}


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip()
    if login.startswith("@"):
        login = login[1:]
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a GitLab username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"GitLab lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No public GitLab.com user with that login.")
    findings = [
        Finding("username", str(data.get("username") or login), "gitlab", "high", str(data.get("web_url") or "")),
    ]
    if data.get("name"):
        findings.append(Finding("name", str(data["name"]), "gitlab", "medium", "Public name"))
    if data.get("web_url"):
        findings.append(Finding("url", str(data["web_url"]), "gitlab", "high", "Profile"))
    if data.get("location"):
        findings.append(Finding("address", str(data["location"]), "gitlab", "low", "Profile location"))
    return ModuleResult(status="ok", findings=findings)
