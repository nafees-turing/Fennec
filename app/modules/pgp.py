import re
from urllib.parse import quote

from app.modules.base import Finding, ModuleResult, ModuleSpec

EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
SPEC = ModuleSpec(
    id="pgp",
    title="PGP",
    milestone="later",
    summary="One keys.openpgp.org lookup by email. Presence only, not the private key.",
    input_label="Email",
    placeholder="name@example.com",
    available=True,
    network=True,
    category="basic",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_key(email: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://keys.openpgp.org/vks/v1/by-email/{quote(email)}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/pgp-keys, text/plain"},
        timeout=8.0,
    )
    if response.status_code == 404:
        return {"found": False, "text": ""}
    response.raise_for_status()
    return {"found": True, "text": response.text[:200]}


def run(raw: str, scanner=None) -> ModuleResult:
    email = raw.strip().lower()
    if not EMAIL.fullmatch(email):
        return ModuleResult(status="failed", error="Enter an email address.")
    scanner = scanner or fetch_key
    try:
        data = scanner(email)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"PGP lookup failed: {exc}")
    findings = [Finding("email", email, "keys.openpgp.org", "high", "WKD/VKS email search")]
    if data.get("found"):
        findings.append(
            Finding("account", "keys.openpgp.org", "keys.openpgp.org", "medium", "A public key is published for this address.")
        )
    else:
        findings.append(Finding("note", "no published key", "keys.openpgp.org", "low", "No public key for this address."))
    return ModuleResult(status="ok", findings=findings)
