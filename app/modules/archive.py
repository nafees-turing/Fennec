from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.domain import HOST, normalize_host

SPEC = ModuleSpec(
    id="archive",
    title="Web archive",
    milestone="later",
    summary="One Wayback Machine availability check. No full URL dump.",
    input_label="Domain or URL",
    placeholder="example.com",
    available=True,
    network=True,
    category="network",
)

USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_archive(url: str) -> dict:
    import httpx

    target = url if "://" in url else f"https://{url}"
    response = httpx.get(
        "https://archive.org/wayback/available",
        params={"url": target},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=10.0,
    )
    response.raise_for_status()
    snap = ((response.json().get("archived_snapshots") or {}).get("closest") or {})
    return {
        "available": bool(snap.get("available")),
        "url": snap.get("url") or "",
        "timestamp": snap.get("timestamp") or "",
        "status": str(snap.get("status") or ""),
    }


def run(raw: str, scanner=None) -> ModuleResult:
    host = normalize_host(raw)
    if not HOST.fullmatch(host):
        return ModuleResult(status="failed", error="Enter a domain such as example.com.")
    scanner = scanner or fetch_archive
    try:
        snap = scanner(host)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Wayback check failed: {exc}")
    findings = [Finding("domain", host, "wayback", "high", "Wayback availability check")]
    if snap.get("available") and snap.get("url"):
        findings.append(
            Finding(
                "url",
                snap["url"],
                "wayback",
                "medium",
                f"Closest snapshot {snap.get('timestamp')} HTTP {snap.get('status')}",
            )
        )
    else:
        findings.append(Finding("url", host, "wayback", "low", "No snapshot reported for this host."))
    return ModuleResult(status="ok", findings=findings)
