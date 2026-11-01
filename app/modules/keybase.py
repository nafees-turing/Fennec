import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9._-]{2,39}$")
SPEC = ModuleSpec(
    id="keybase",
    title="Keybase",
    milestone="later",
    summary="One Keybase user lookup, including public proofs.",
    input_label="Keybase username",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_user(login: str) -> dict:
    import httpx

    response = httpx.get(
        "https://keybase.io/_/api/1.0/user/lookup.json",
        params={"username": login},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip()
    if login.startswith("@"):
        login = login[1:]
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a Keybase username.")
    scanner = scanner or fetch_user
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Keybase lookup failed: {exc}")
    if data.get("status", {}).get("code") not in {0, None} or not data.get("them"):
        return ModuleResult(status="failed", error="No Keybase user with that login.")
    them = data.get("them") or {}
    basics = them.get("basics") or {}
    profile = them.get("profile") or {}
    findings = [
        Finding("username", str(basics.get("username") or login), "keybase", "high", f"https://keybase.io/{login}"),
    ]
    if profile.get("full_name"):
        findings.append(Finding("name", str(profile["full_name"]), "keybase", "medium", "Keybase full name"))
    if profile.get("location"):
        findings.append(Finding("address", str(profile["location"]), "keybase", "low", "Keybase location"))
    if profile.get("bio"):
        findings.append(Finding("note", str(profile["bio"]), "keybase", "low", "Bio"))
    proofs = ((them.get("proofs_summary") or {}).get("all") or [])[:10]
    for proof in proofs:
        nametag = proof.get("nametag") or proof.get("proof_type")
        url = proof.get("service_url") or proof.get("proof_url") or ""
        if nametag:
            findings.append(
                Finding("account", str(url or nametag), "keybase", "medium", str(proof.get("proof_type") or "proof"))
            )
    return ModuleResult(status="ok", findings=findings)
