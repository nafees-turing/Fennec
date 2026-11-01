import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
SPEC = ModuleSpec(
    id="github",
    title="GitHub",
    milestone="later",
    summary="One GitHub API user lookup. Public profile fields only.",
    input_label="GitHub username",
    placeholder="octocat",
    available=True,
    network=True,
    category="social",
)

USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://api.github.com/users/{login}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=8.0,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip()
    if login.startswith("@"):
        login = login[1:]
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a GitHub username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"GitHub lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No public GitHub user with that login.")
    findings = [
        Finding("username", str(data.get("login") or login), "github", "high", str(data.get("html_url") or "")),
    ]
    if data.get("name"):
        findings.append(Finding("name", str(data["name"]), "github", "medium", "Public profile name"))
    if data.get("company"):
        findings.append(Finding("company", str(data["company"]).strip("@ "), "github", "low", "Profile company field"))
    if data.get("blog"):
        findings.append(Finding("url", str(data["blog"]), "github", "medium", "Profile website"))
    if data.get("location"):
        findings.append(Finding("address", str(data["location"]), "github", "low", "Profile location, not GPS"))
    if data.get("email"):
        findings.append(Finding("email", str(data["email"]), "github", "medium", "Public profile email"))
    if data.get("bio"):
        findings.append(Finding("note", str(data["bio"]), "github", "low", "Bio"))
    return ModuleResult(status="ok", findings=findings)
