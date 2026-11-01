import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_-]{2,30}$")
SPEC = ModuleSpec(
    id="lichess",
    title="Lichess",
    milestone="later",
    summary="One Lichess public user profile.",
    input_label="Lichess username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://lichess.org/api/user/{login}",
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
        return ModuleResult(status="failed", error="Enter a Lichess username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Lichess failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No Lichess user with that name.")
    profile = data.get("profile") or {}
    findings = [
        Finding("username", str(data.get("username") or login), "lichess", "high", f"https://lichess.org/@/{login}"),
    ]
    if profile.get("realName"):
        findings.append(Finding("name", str(profile["realName"]), "lichess", "medium", "Real name field"))
    if profile.get("location"):
        findings.append(Finding("address", str(profile["location"]), "lichess", "low", "Location field"))
    if profile.get("bio"):
        findings.append(Finding("note", str(profile["bio"])[:400], "lichess", "low", "Bio"))
    if profile.get("links"):
        findings.append(Finding("url", str(profile["links"]), "lichess", "medium", "Profile links"))
    return ModuleResult(status="ok", findings=findings)
