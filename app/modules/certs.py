from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.domain import HOST, normalize_host

SPEC = ModuleSpec(
    id="certs",
    title="Certificates",
    milestone="later",
    summary="One crt.sh query. Stores a short list of names from Certificate Transparency.",
    input_label="Domain",
    placeholder="example.com",
    available=True,
    network=True,
    category="network",
)

USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_certs(host: str) -> list[str]:
    import httpx

    response = httpx.get(
        "https://crt.sh/",
        params={"q": host, "output": "json"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=12.0,
    )
    response.raise_for_status()
    names: list[str] = []
    seen: set[str] = set()
    for row in response.json()[:80]:
        raw = str(row.get("name_value") or "")
        for item in raw.split("\n"):
            name = item.strip().lower().lstrip("*.")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
            if len(names) >= 15:
                return names
    return names


def run(raw: str, scanner=None) -> ModuleResult:
    host = normalize_host(raw)
    if not HOST.fullmatch(host):
        return ModuleResult(status="failed", error="Enter a domain such as example.com.")
    scanner = scanner or fetch_certs
    try:
        names = scanner(host)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"crt.sh failed: {exc}")
    findings = [
        Finding("domain", host, "crt.sh", "high", f"{len(names)} certificate names (capped at 15)"),
    ]
    for name in names:
        findings.append(Finding("cert_name", name, "crt.sh", "medium", "Certificate Transparency"))
    return ModuleResult(status="ok", findings=findings)
