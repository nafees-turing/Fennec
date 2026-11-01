import ipaddress
import os
from pathlib import Path

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="geoip",
    title="GeoIP",
    milestone="later",
    summary="Country for an IP from a local MaxMind or DB-IP mmdb. No network.",
    input_label="IPv4 or IPv6 address",
    placeholder="1.1.1.1",
    available=True,
    network=False,
)


def database_path() -> Path:
    env = os.environ.get("FENNEC_GEOLITE", "").strip()
    if env:
        return Path(env)
    return Path("data") / "GeoLite2-Country.mmdb"


def lookup_ip(ip: str) -> dict:
    path = database_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"No GeoIP database at {path}. Download GeoLite2-Country.mmdb from MaxMind "
            "and put it in data/, or set FENNEC_GEOLITE."
        )
    import geoip2.database
    import geoip2.errors

    with geoip2.database.Reader(str(path)) as reader:
        try:
            record = reader.city(ip)
            city = record.city.name or ""
        except geoip2.errors.InvalidModelError:
            record = reader.country(ip)
            city = ""
        return {
            "country": record.country.name or "",
            "iso": record.country.iso_code or "",
            "city": city,
            "source": path.name,
        }


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

    findings = [Finding("ip", text, row.get("source") or "geoip", "high", "Looked up in a local mmdb.")]
    if row.get("country"):
        findings.append(
            Finding("country", row["country"], row.get("source") or "geoip", "medium", row.get("iso") or "")
        )
    if row.get("city"):
        findings.append(Finding("city", row["city"], row.get("source") or "geoip", "low", "City from local GeoIP."))
    return ModuleResult(status="ok", findings=findings)
