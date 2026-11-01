import ipaddress

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="internetdb",
    title="InternetDB",
    milestone="later",
    summary="One keyless Shodan InternetDB lookup: hostnames, ports, and CPEs already in their index.",
    input_label="IPv4 address",
    placeholder="1.1.1.1",
    available=True,
    network=True,
    category="network",
)

USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_internetdb(ip: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://internetdb.shodan.io/{ip}",
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
        return ModuleResult(status="failed", error="Enter an IPv4 or IPv6 address.")
    if addr.version != 4:
        return ModuleResult(status="failed", error="InternetDB is IPv4-only.")
    if not addr.is_global:
        return ModuleResult(status="failed", error="InternetDB is for public addresses.")
    scanner = scanner or fetch_internetdb
    try:
        data = scanner(text)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"InternetDB failed: {exc}")
    from app.modules.geoip import location_findings

    findings = [Finding("ip", text, "internetdb", "high", "Shodan InternetDB, one request, no API key.")]
    findings.extend(location_findings(text))
    for host in (data.get("hostnames") or [])[:12]:
        findings.append(Finding("hostname", str(host), "internetdb", "medium", "Indexed hostname"))
    for port in (data.get("ports") or [])[:20]:
        findings.append(Finding("port", str(port), "internetdb", "medium", "Open port in Shodan's index, not a live scan from this machine."))
    for cpe in (data.get("cpes") or [])[:12]:
        findings.append(Finding("software", str(cpe), "internetdb", "low", "CPE from banners"))
    for vuln in (data.get("vulns") or [])[:8]:
        findings.append(Finding("cve", str(vuln), "internetdb", "low", "CVE tag in the index. Confirm before acting."))
    return ModuleResult(status="ok", findings=findings)
