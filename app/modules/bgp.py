import ipaddress

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="bgp",
    title="BGP",
    milestone="later",
    summary="One BGPView lookup for prefix and origin ASN.",
    input_label="IPv4 or IPv6 address",
    placeholder="1.1.1.1",
    available=True,
    network=True,
    category="network",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_bgp(ip: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://api.bgpview.io/ip/{ip}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    return response.json().get("data") or {}


def run(raw: str, scanner=None) -> ModuleResult:
    text = raw.strip()
    try:
        addr = ipaddress.ip_address(text)
    except ValueError:
        return ModuleResult(status="failed", error="Enter an IPv4 or IPv6 address.")
    if not addr.is_global:
        return ModuleResult(status="failed", error="BGP lookup is for public addresses.")
    scanner = scanner or fetch_bgp
    try:
        data = scanner(text)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"BGPView failed: {exc}")
    findings = [Finding("ip", text, "bgpview", "high", "BGPView IP query")]
    prefixes = data.get("prefixes") or data.get("ipv4_prefixes") or data.get("ipv6_prefixes") or []
    for row in prefixes[:6]:
        prefix = str(row.get("prefix") or "")
        asn = row.get("asn") or {}
        if isinstance(asn, dict):
            number = asn.get("asn")
            org = asn.get("name") or asn.get("description") or ""
        else:
            number, org = asn, ""
        if prefix:
            findings.append(Finding("prefix", prefix, "bgpview", "medium", org or "Announced prefix"))
        if number is not None:
            findings.append(Finding("asn", f"AS{number}", "bgpview", "medium", org))
        if org:
            findings.append(Finding("org", str(org), "bgpview", "medium", "Origin AS name"))
    rir = data.get("rir_allocation") or {}
    if rir.get("rir_name"):
        findings.append(Finding("rir", str(rir["rir_name"]), "bgpview", "low", str(rir.get("prefix") or "")))
    return ModuleResult(status="ok", findings=findings)
