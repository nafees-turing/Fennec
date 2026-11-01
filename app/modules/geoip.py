import ipaddress
import os
from pathlib import Path

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="geoip",
    title="IP network",
    milestone="later",
    summary="Local only: scope, ASN, and country/city from DB-IP or GeoLite mmdb files. Not GPS.",
    input_label="IPv4 or IPv6 address",
    placeholder="1.1.1.1",
    available=True,
    network=False,
    category="network",
)

ROOT = Path(__file__).resolve().parents[2]


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def database_path() -> Path:
    env = os.environ.get("FENNEC_GEOLITE", "").strip()
    if env:
        return Path(env)
    intel = ROOT.parent / "netwatch" / "data" / "intel"
    found = _first_existing(
        [
            Path("data") / "dbip-city-lite.mmdb",
            Path("data") / "dbip-country-lite.mmdb",
            Path("data") / "GeoLite2-City.mmdb",
            Path("data") / "GeoLite2-Country.mmdb",
            intel / "dbip-city-lite.mmdb",
            intel / "dbip-country-lite.mmdb",
        ]
    )
    return found or Path("data") / "dbip-city-lite.mmdb"


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
            subdiv = ""
            if record.subdivisions and record.subdivisions.most_specific.name:
                subdiv = record.subdivisions.most_specific.name
            lat = record.location.latitude
            lon = record.location.longitude
        except geoip2.errors.InvalidModelError:
            record = reader.country(ip)
            city, subdiv, lat, lon = "", "", None, None
        except geoip2.errors.AddressNotFoundError:
            return {"source_geo": path.name}
    return {
        "country": record.country.name or "",
        "iso": record.country.iso_code or "",
        "city": city,
        "region": subdiv,
        "lat": lat,
        "lon": lon,
        "source_geo": path.name,
    }


def lookup_ip(ip: str) -> dict:
    row = {"scope": classify(ip)}
    row.update(lookup_asn(ip))
    row.update(lookup_geo(ip))
    return row


def location_findings(ip: str) -> list[Finding]:
    """Country/city/ASN from local mmdb. Safe to call from other modules."""
    try:
        addr = ipaddress.ip_address(ip.strip().split()[0])
    except ValueError:
        return []
    if not addr.is_global:
        return []
    try:
        row = lookup_ip(str(addr))
    except Exception:
        return []
    source = row.get("source_geo") or row.get("source_asn") or "geoip"
    out: list[Finding] = []
    if row.get("asn"):
        out.append(Finding("asn", row["asn"], row.get("source_asn") or source, "medium", row.get("asn_org") or "DB-IP ASN Lite"))
    if row.get("asn_org"):
        out.append(Finding("org", row["asn_org"], row.get("source_asn") or source, "medium", "Autonomous system organisation"))
    if row.get("country"):
        out.append(Finding("country", row["country"], source, "medium", row.get("iso") or "IP range, not GPS"))
    if row.get("region"):
        out.append(Finding("region", row["region"], source, "low", "IP-range subdivision"))
    if row.get("city"):
        out.append(Finding("city", row["city"], source, "low", "IP-range city, not a live location"))
    if row.get("lat") is not None and row.get("lon") is not None:
        out.append(
            Finding("coords", f"{row['lat']},{row['lon']}", source, "low", "Approximate centroid of the IP block.")
        )
    return out


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
    if row.get("region"):
        findings.append(
            Finding("region", row["region"], row.get("source_geo") or "geoip", "low", "Subdivision from the IP range, not GPS.")
        )
    if row.get("city"):
        findings.append(
            Finding("city", row["city"], row.get("source_geo") or "geoip", "low", "City from the IP range, not a live location.")
        )
    if row.get("lat") is not None and row.get("lon") is not None:
        findings.append(
            Finding(
                "coords",
                f"{row['lat']},{row['lon']}",
                row.get("source_geo") or "geoip",
                "low",
                "Approximate centroid of the IP block. Often tens of kilometres off.",
            )
        )
    if not row.get("country") and not row.get("source_geo"):
        findings.append(
            Finding(
                "note",
                "no location database",
                "fennec",
                "low",
                "Drop dbip-city-lite.mmdb (CC-BY from db-ip.com/db/lite.php) into data/ for country/city.",
            )
        )
    return ModuleResult(status="ok", findings=findings)
