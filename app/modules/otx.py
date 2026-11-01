import ipaddress

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="otx",
    title="OTX",
    milestone="later",
    summary="One AlienVault OTX indicator lookup. Pulse count and reputation only.",
    input_label="IPv4 address",
    placeholder="1.1.1.1",
    available=True,
    network=True,
    category="network",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_indicator(ip: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://otx.alienvault.com/api/v1/indicators/IPv4/{ip}/general",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    if response.status_code == 404:
        return {}
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    text = raw.strip()
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return ModuleResult(status="failed", error="Enter an IPv4 address.")
    if addr.version != 4 or not addr.is_global:
        return ModuleResult(status="failed", error="OTX general lookup is for public IPv4.")
    scanner = scanner or fetch_indicator
    try:
        data = scanner(text)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"OTX lookup failed: {exc}")
    from app.modules.geoip import location_findings

    findings = [Finding("ip", text, "otx", "high", "AlienVault OTX, one request.")]
    findings.extend(location_findings(text))
    pulses = (data.get("pulse_info") or {}).get("count")
    if pulses is not None:
        findings.append(Finding("note", f"{pulses} pulses", "otx", "medium", "Community pulses mentioning this IP"))
    if data.get("reputation") is not None:
        findings.append(Finding("note", f"reputation {data['reputation']}", "otx", "low", "OTX reputation score"))
    if data.get("country_name"):
        findings.append(Finding("country", str(data["country_name"]), "otx", "medium", "OTX country"))
    if data.get("asn"):
        findings.append(Finding("asn", str(data["asn"]), "otx", "medium", "OTX ASN"))
    return ModuleResult(status="ok", findings=findings)
