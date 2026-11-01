import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="geocode",
    title="Geocode",
    milestone="later",
    summary="One OpenStreetMap Nominatim search. Not a live GPS fix.",
    input_label="Place or postal line",
    placeholder="221B Baker Street, London",
    available=True,
    network=True,
    category="addresses",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def search_place(query: str) -> list[dict]:
    import httpx

    response = httpx.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": "1"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=10.0,
    )
    response.raise_for_status()
    return list(response.json() or [])[:1]


def run(raw: str, scanner=None) -> ModuleResult:
    query = re.sub(r"\s+", " ", raw).strip()
    if len(query) < 5 or len(query) > 200:
        return ModuleResult(status="failed", error="Enter a short place or postal line.")
    scanner = scanner or search_place
    try:
        rows = scanner(query)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Nominatim failed: {exc}")
    findings = [Finding("address", query, "nominatim", "high", "OpenStreetMap search")]
    if not rows:
        findings.append(Finding("note", "no match", "nominatim", "low", "No geocode hit."))
        return ModuleResult(status="ok", findings=findings)
    row = rows[0]
    label = str(row.get("display_name") or query)
    lat, lon = row.get("lat"), row.get("lon")
    findings.append(Finding("place", label, "nominatim", "medium", f"{row.get('type') or ''} {row.get('class') or ''}".strip()))
    if lat and lon:
        findings.append(Finding("coords", f"{lat},{lon}", "nominatim", "medium", "Map coordinates from OSM, not a phone location."))
    return ModuleResult(status="ok", findings=findings)
