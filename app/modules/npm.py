import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9._~-]{2,39}$")
SPEC = ModuleSpec(
    id="npm",
    title="npm",
    milestone="later",
    summary="One npm registry user lookup.",
    input_label="npm username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://registry.npmjs.org/-/user/org.couchdb.user:{login}",
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
        return ModuleResult(status="failed", error="Enter an npm username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"npm lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No npm user with that name.")
    findings = [
        Finding("username", str(data.get("name") or login), "npm", "high", f"https://www.npmjs.com/~{login}"),
    ]
    if data.get("email"):
        findings.append(Finding("email", str(data["email"]), "npm", "medium", "Public npm email"))
    if data.get("homepage"):
        findings.append(Finding("url", str(data["homepage"]), "npm", "medium", "Homepage"))
    return ModuleResult(status="ok", findings=findings)
