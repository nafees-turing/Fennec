import hashlib
import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
SPEC = ModuleSpec(
    id="gravatar",
    title="Gravatar",
    milestone="later",
    summary="One Gravatar profile request from the email hash.",
    input_label="Email",
    placeholder="name@example.com",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_profile(email: str) -> dict:
    import httpx

    digest = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    response = httpx.get(
        f"https://www.gravatar.com/{digest}.json",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
        follow_redirects=True,
    )
    if response.status_code == 404:
        return {"hash": digest, "entry": None}
    response.raise_for_status()
    payload = response.json()
    entries = payload.get("entry") or []
    return {"hash": digest, "entry": entries[0] if entries else None}


def run(raw: str, scanner=None) -> ModuleResult:
    email = raw.strip().lower()
    if not EMAIL.fullmatch(email):
        return ModuleResult(status="failed", error="Enter an email address.")
    scanner = scanner or fetch_profile
    try:
        data = scanner(email)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Gravatar failed: {exc}")
    digest = data.get("hash") or ""
    findings = [
        Finding("email", email, "gravatar", "high", f"md5={digest}"),
        Finding("url", f"https://www.gravatar.com/avatar/{digest}", "gravatar", "medium", "Avatar URL (may be the default mystery-person)"),
    ]
    entry = data.get("entry")
    if not entry:
        findings.append(Finding("account", "gravatar", "gravatar", "low", "No public Gravatar profile JSON."))
        return ModuleResult(status="ok", findings=findings)
    display = entry.get("displayName") or entry.get("preferredUsername")
    if display:
        findings.append(Finding("name", str(display), "gravatar", "medium", "Gravatar display name"))
    if entry.get("profileUrl"):
        findings.append(Finding("url", str(entry["profileUrl"]), "gravatar", "high", "Gravatar profile"))
    for account in (entry.get("accounts") or [])[:8]:
        url = account.get("url") or account.get("domain")
        if url:
            findings.append(Finding("account", str(url), "gravatar", "medium", str(account.get("shortname") or "linked")))
    return ModuleResult(status="ok", findings=findings)
