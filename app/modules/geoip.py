import ipaddress
import os
from pathlib import Path

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="geoip",
    title="IP network",
    milestone="later",
    summary="Local only: address scope, ASN/org from a DB-IP lite file, country if an mmdb is present.",
    input_label="IPv4 or IPv6 address",
    placeholder="1.1.1.1",
    available=True,
    network=False,
)

ROOT = Path(__file__).resolve().parents[2]


def database_path() -> Path:
    env = os.environ.get("FENNEC_GEOLITE", "").strip()
    if env:
        return Path(env)
    return Path("data") / "GeoLite2-Country.mmdb"


def asn_path() -> Path:
    env = os.environ.get("FENNEC_ASN", "").strip()
    if env:
        return Path(env)
    local = Path("data") / "dbip-asn-lite.mmdb"
    if local.is_file():
        return local
    sibling = ROOT.parent / "netwatch" / "data" / "intel" / "dbip-asn-lite.mmdb"
    if sibling.is_file():
        return sibling
    return local


def classify(ip: str) -> str:
    addr = ipaddress.ip_address(ip)
    if addr.is_loopback:
        return "loopback"
    if addr.is_private:
        return "private"
    if addr.is_link_local:
        return "link-local"
    if addr.is_multicast:
        return "multicast"
    if addr.is_reserved or addr.is_unspecified:
        return "reserved"
    if addr.is_global:
        return "global"
    return "other"


def lookup_asn(ip: str) -> dict:
    path = asn_path()
    if not path.is_file():
        return {}
    import maxminddb

    with maxminddb.open_database(str(path)) as reader:
        record = reader.get(ip)
    if not isinstance(record, dict):
        return {}
    number = record.get("autonomous_system_number")
    org = str(record.get("autonomous_system_organization") or "").strip()
    out = {"source_asn": path.name}
    if number is not None:
        out["asn"] = f"AS{number}"
    if org:
        out["asn_org"] = org
    return out


def lookup_geo(ip: str) -> dict:
    path = database_path()
    if not path.is_file():
        return {}
    import geoip2.database
    import geoip2.errors

    with geoip2.database.Reader(str(path)) as reader:
        try:
            record = reader.city(ip)
            city = record.city.name or ""
        except geoip2.errors.InvalidModelError:
            record = reader.country(ip)
            city = ""
        except geoip2.errors.AddressNotFoundError:
            return {"source_geo": path.name}
    return {
        "country": record.country.name or "",
        "iso": record.country.iso_code or "",
        "city": city,
        "source_geo": path.name,
    }


def lookup_ip(ip: str) -> dict:
    row = {"scope": classify(ip)}
    row.update(lookup_asn(ip))
    row.update(lookup_geo(ip))
    return row


def run(raw: str, lookup=None) -> ModuleResult:
    text = raw.strip()
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return ModuleResult(status="failed", error="Enter an IPv4 or IPv6 address.")

    lookup = lookup or lookup_ip
    try:
        row = lookup(text)
    except Exception as exc:
        return ModuleResult(status="failed", error=str(exc))

    source = row.get("source_asn") or row.get("source_geo") or "ipaddress"
    findings = [
        Finding("ip", text, source, "high", "Local classification. No remote IP API."),
        Finding("scope", row.get("scope") or "other", "ipaddress", "high", "From the address itself."),
    ]
    if row.get("asn"):
        findings.append(
            Finding("asn", row["asn"], row.get("source_asn") or "asn", "medium", row.get("asn_org") or "DB-IP ASN Lite")
        )
    if row.get("asn_org"):
        findings.append(
            Finding("org", row["asn_org"], row.get("source_asn") or "asn", "medium", "Autonomous system organisation")
        )
    if row.get("country"):
        findings.append(
            Finding("country", row["country"], row.get("source_geo") or "geoip", "medium", row.get("iso") or "")
        )
    if row.get("city"):
        findings.append(
            Finding("city", row["city"], row.get("source_geo") or "geoip", "low", "City from a local mmdb.")
        )
    return ModuleResult(status="ok", findings=findings)
