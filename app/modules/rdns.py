import ipaddress

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="rdns",
    title="Reverse DNS",
    milestone="later",
    summary="One PTR lookup for an IP. No port scan.",
    input_label="IPv4 or IPv6 address",
    placeholder="1.1.1.1",
    available=True,
    network=True,
    category="network",
)


def lookup_ptr(ip: str) -> list[str]:
    import dns.resolver
    import dns.reversename

    name = dns.reversename.from_address(ip)
    resolver = dns.resolver.Resolver()
    resolver.lifetime = 5.0
    try:
        answers = resolver.resolve(name, "PTR")
    except Exception:
        return []
    return [str(item).rstrip(".") for item in answers]


def run(raw: str, lookup=None) -> ModuleResult:
    text = raw.strip()
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return ModuleResult(status="failed", error="Enter an IPv4 or IPv6 address.")
    lookup = lookup or lookup_ptr
    try:
        names = lookup(text)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"PTR lookup failed: {exc}")
    findings = [Finding("ip", text, "dnspython", "high", "Reverse DNS (PTR)")]
    if not names:
        findings.append(Finding("hostname", "(none)", "dnspython", "low", "No PTR record for this address."))
        return ModuleResult(status="ok", findings=findings)
    for name in names:
        findings.append(Finding("hostname", name, "dnspython", "high", "PTR record"))
    return ModuleResult(status="ok", findings=findings)
