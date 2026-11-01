import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_-]{2,30}$")
SPEC = ModuleSpec(
    id="devto",
    title="DEV",
    milestone="later",
    summary="One DEV.to public user lookup.",
    input_label="DEV username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        "https://dev.to/api/users/by_username",
        params={"url": login},
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
        return ModuleResult(status="failed", error="Enter a DEV.to username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"DEV.to failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No DEV.to user with that name.")
    findings = [
        Finding("username", str(data.get("username") or login), "devto", "high", f"https://dev.to/{login}"),
    ]
    if data.get("name"):
        findings.append(Finding("name", str(data["name"]), "devto", "medium", "Display name"))
    if data.get("summary"):
        findings.append(Finding("note", str(data["summary"])[:400], "devto", "low", "Bio"))
    if data.get("location"):
        findings.append(Finding("address", str(data["location"]), "devto", "low", "Location"))
    if data.get("website_url"):
        findings.append(Finding("url", str(data["website_url"]), "devto", "medium", "Website"))
    if data.get("twitter_username"):
        findings.append(Finding("username", str(data["twitter_username"]), "devto", "medium", "Twitter handle on DEV"))
    if data.get("github_username"):
        findings.append(Finding("username", str(data["github_username"]), "devto", "medium", "GitHub handle on DEV"))
    return ModuleResult(status="ok", findings=findings)
