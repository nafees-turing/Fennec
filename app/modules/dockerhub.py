import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9._-]{2,39}$")
SPEC = ModuleSpec(
    id="dockerhub",
    title="Docker Hub",
    milestone="later",
    summary="One Docker Hub user lookup.",
    input_label="Docker Hub username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://hub.docker.com/v2/users/{login}/",
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
        return ModuleResult(status="failed", error="Enter a Docker Hub username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Docker Hub lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No Docker Hub user with that name.")
    findings = [
        Finding("username", str(data.get("username") or login), "dockerhub", "high", f"https://hub.docker.com/u/{login}"),
    ]
    full = data.get("full_name") or data.get("name")
    if full:
        findings.append(Finding("name", str(full), "dockerhub", "medium", "Profile name"))
    if data.get("location"):
        findings.append(Finding("address", str(data["location"]), "dockerhub", "low", "Profile location"))
    if data.get("company"):
        findings.append(Finding("company", str(data["company"]), "dockerhub", "low", "Profile company"))
    return ModuleResult(status="ok", findings=findings)
