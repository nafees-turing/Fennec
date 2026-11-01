import re
from urllib.parse import urlparse

from app.modules.base import Finding, ModuleResult, ModuleSpec

HOST = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")

SPEC = ModuleSpec(
    id="domain",
    title="Domain",
    milestone="M4",
    summary="DNS records plus registrar data (RDAP first, WHOIS if needed).",
    input_label="Domain or URL",
    placeholder="example.com",
    available=True,
    network=True,
    category="network",
)


def normalize_host(raw: str) -> str:
    text = raw.strip().lower()
    if "://" not in text:
        text = "https://" + text
    parsed = urlparse(text)
    host = (parsed.hostname or "").strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def lookup_dns(domain: str) -> dict[str, list[str]]:
    import dns.resolver

    resolver = dns.resolver.Resolver()
    resolver.lifetime = 5.0
    out: dict[str, list[str]] = {}
    for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
        try:
            answers = resolver.resolve(domain, rtype)
            out[rtype] = [rr.to_text().strip('"') for rr in answers]
        except Exception:
            out[rtype] = []
    return out


def lookup_whois(domain: str) -> dict:
    import whoisdomain

    record = whoisdomain.query(domain, rdapOnly=True, timeout=10) or whoisdomain.query(
        domain, timeout=10
    )
    if record is None:
        return {}

    def stamp(value) -> str:
        if value is None:
            return ""
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    return {
        "registrar": record.registrar or "",
        "registrant": record.registrant or "",
        "registrant_country": record.registrant_country or "",
        "creation_date": stamp(record.creation_date),
        "expiration_date": stamp(record.expiration_date),
        "updated_date": stamp(record.updated_date),
        "name_servers": list(record.name_servers or []),
        "emails": list(record.emails or []),
        "status": record.status or "",
        "source": getattr(record, "__lookup__", "rdap"),
    }


def run(raw: str, dns_lookup=None, whois_lookup=None) -> ModuleResult:
    host = normalize_host(raw)
    if not HOST.fullmatch(host):
        return ModuleResult(status="failed", error="Enter a domain such as example.com.")

    dns_lookup = dns_lookup or lookup_dns
    whois_lookup = whois_lookup or lookup_whois
    dns_error = None
    whois_error = None
    try:
        records = dns_lookup(host)
    except Exception as exc:
        records = {}
        dns_error = str(exc)
    try:
        registration = whois_lookup(host)
    except Exception as exc:
        registration = {}
        whois_error = str(exc)

    findings: list[Finding] = [Finding("domain", host, "fennec", "high", "Normalized host.")]
    kind_for = {"A": "ip", "AAAA": "ipv6", "MX": "mx", "NS": "nameserver", "TXT": "txt"}
    for rtype, values in records.items():
        kind = kind_for.get(rtype, rtype.lower())
        for value in values:
            if not value:
                continue
            findings.append(Finding(kind, value, "dnspython", "high", f"{rtype} record"))

    whois_source = str(registration.get("source") or "whoisdomain")
    mapping = [
        ("registrar", "registrar"),
        ("registrant", "registrant"),
        ("registrant_country", "country"),
        ("creation_date", "created"),
        ("expiration_date", "expires"),
        ("updated_date", "updated"),
        ("status", "status"),
    ]
    for key, kind in mapping:
        value = str(registration.get(key) or "").strip()
        if value:
            findings.append(Finding(kind, value, whois_source, "medium", key.replace("_", " ")))
    for server in registration.get("name_servers") or []:
        if server:
            findings.append(Finding("nameserver", str(server).rstrip("."), whois_source, "medium", "WHOIS nameserver"))
    for address in registration.get("emails") or []:
        if address:
            findings.append(Finding("email", str(address).lower(), whois_source, "medium", "WHOIS contact email"))

    dns_hits = any(records.get(key) for key in ("A", "AAAA", "MX", "NS", "TXT"))
    whois_hits = any(registration.get(key) for key in ("registrar", "registrant", "creation_date", "name_servers"))
    if not dns_hits and not whois_hits:
        parts = [item for item in (dns_error, whois_error) if item]
        return ModuleResult(
            status="failed",
            error="; ".join(parts) or "No DNS or registration data for that domain.",
        )
    return ModuleResult(status="ok", findings=findings)
