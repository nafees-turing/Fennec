import re

from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.profiles import probe

USER = re.compile(r"^[A-Za-z0-9_]{1,15}$")
SPEC = ModuleSpec(
    id="twitter",
    title="X / Twitter",
    milestone="later",
    summary="One public GET of x.com/handle. Login walls often return 403; that is not stored as a hit.",
    input_label="X username",
    placeholder="handle",
    available=True,
    network=True,
    category="social",
)


def fetch_profile(login: str) -> dict:
    return probe(f"https://x.com/{login}")


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip().lstrip("@")
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter an X/Twitter handle (up to 15 letters, digits, _).")
    scanner = scanner or fetch_profile
    try:
        row = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"X lookup failed: {exc}")
    findings = [Finding("username", login, "x.com", "high", "Public profile URL check only.")]
    if row.get("exists") and row.get("url"):
        findings.append(
            Finding("account", str(row["url"]), "x.com", "medium", f"HTTP {row.get('status')} on a public URL")
        )
    return ModuleResult(status="ok", findings=findings)
