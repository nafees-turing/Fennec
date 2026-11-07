import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_]{3,20}$")
SPEC = ModuleSpec(
    id="roblox",
    title="Roblox",
    milestone="later",
    summary="One public Roblox username lookup. Display name and bio only.",
    input_label="Roblox username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.post(
        "https://users.roblox.com/v1/usernames/users",
        json={"usernames": [login], "excludeBannedUsers": False},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    rows = (response.json() or {}).get("data") or []
    if not rows:
        return {}
    user = rows[0]
    detail = httpx.get(
        f"https://users.roblox.com/v1/users/{user.get('id')}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    if detail.status_code == 200:
        user = {**user, **(detail.json() or {})}
    return user


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip().lstrip("@")
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a Roblox username (3–20 characters).")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Roblox lookup failed: {exc}")
    if not data:
        return ModuleResult(status="failed", error="No Roblox user with that name.")
    user_id = data.get("id")
    findings = [
        Finding(
            "username",
            str(data.get("name") or login),
            "roblox",
            "high",
            f"https://www.roblox.com/users/{user_id}/profile" if user_id else "Public username lookup",
        )
    ]
    if data.get("displayName"):
        findings.append(
            Finding("name", str(data["displayName"]), "roblox", "medium", str(data.get("description") or "Display name")[:300])
        )
    return ModuleResult(status="ok", findings=findings)
