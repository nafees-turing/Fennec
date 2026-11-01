from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.domain import HOST, normalize_host

SPEC = ModuleSpec(
    id="securitytxt",
    title="security.txt",
    milestone="later",
    summary="One GET of /.well-known/security.txt. Contact emails if published.",
    input_label="Domain",
    placeholder="example.com",
    available=True,
    network=True,
    category="network",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_securitytxt(host: str) -> str:
    import httpx

    url = f"https://{host}/.well-known/security.txt"
    response = httpx.get(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
        timeout=8.0,
        follow_redirects=True,
    )
    if response.status_code >= 400:
        return ""
    return response.text[:4000]


def run(raw: str, scanner=None) -> ModuleResult:
    host = normalize_host(raw)
    if not HOST.fullmatch(host):
        return ModuleResult(status="failed", error="Enter a domain such as example.com.")
    scanner = scanner or fetch_securitytxt
    try:
        text = scanner(host)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"security.txt failed: {exc}")
    findings = [Finding("domain", host, "security.txt", "high", "RFC 9116 well-known file")]
    if not text.strip():
        findings.append(Finding("note", "missing", "security.txt", "low", "No security.txt at /.well-known/security.txt"))
        return ModuleResult(status="ok", findings=findings)
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip().lower(), value.strip()
        if key == "contact" and value:
            kind = "email" if value.lower().startswith("mailto:") else "url"
            findings.append(Finding(kind, value.replace("mailto:", ""), "security.txt", "medium", "Contact"))
        elif key in {"policy", "acknowledgments", "canonical", "hiring", "encryption"} and value:
            findings.append(Finding("url", value, "security.txt", "low", key))
        elif key == "expires" and value:
            findings.append(Finding("note", value, "security.txt", "low", "Expires"))
    return ModuleResult(status="ok", findings=findings)
