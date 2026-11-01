import ipaddress

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="greynoise",
    title="GreyNoise",
    milestone="later",
    summary="One GreyNoise Community lookup: scanner noise vs a known service.",
    input_label="IPv4 address",
    placeholder="1.1.1.1",
    available=True,
    network=True,
    category="network",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_community(ip: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://api.greynoise.io/v3/community/{ip}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    if response.status_code in {404, 429}:
        return {"status": response.status_code, "body": {}}
    response.raise_for_status()
    return {"status": response.status_code, "body": response.json()}


def run(raw: str, scanner=None) -> ModuleResult:
    text = raw.strip()
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return ModuleResult(status="failed", error="Enter an IPv4 address.")
    if addr.version != 4 or not addr.is_global:
        return ModuleResult(status="failed", error="GreyNoise Community is for public IPv4.")
    scanner = scanner or fetch_community
    try:
        payload = scanner(text)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"GreyNoise failed: {exc}")
    if payload.get("status") == 429:
        return ModuleResult(status="failed", error="GreyNoise rate-limited this IP. Try later.")
    data = payload.get("body") or {}
    findings = [Finding("ip", text, "greynoise", "high", "GreyNoise Community, no API key.")]
    if payload.get("status") == 404 or not data:
        findings.append(Finding("note", "not in community index", "greynoise", "low", "No classification."))
        return ModuleResult(status="ok", findings=findings)
    classification = str(data.get("classification") or data.get("noise") or "")
    if classification:
        findings.append(Finding("noise", classification, "greynoise", "medium", "mass-scanner vs benign RIOT vs unknown"))
    if data.get("name"):
        findings.append(Finding("org", str(data["name"]), "greynoise", "medium", "Named service (RIOT) if present"))
    if data.get("riot"):
        findings.append(Finding("note", "riot", "greynoise", "medium", "Known benign service"))
    if data.get("noise"):
        findings.append(Finding("note", "noise", "greynoise", "medium", "Seen as internet background noise"))
    if data.get("link"):
        findings.append(Finding("url", str(data["link"]), "greynoise", "low", "Community page"))
    return ModuleResult(status="ok", findings=findings)
