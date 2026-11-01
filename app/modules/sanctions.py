import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

QUERY = re.compile(r"^[\w .,&'()-]{2,80}$")
SPEC = ModuleSpec(
    id="sanctions",
    title="Sanctions",
    milestone="later",
    summary="One OpenSanctions search. Public list hits only, not a legal determination.",
    input_label="Name or organization",
    placeholder="Example Ltd",
    available=True,
    network=True,
    category="addresses",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def search_sanctions(query: str) -> list[dict]:
    import httpx

    response = httpx.get(
        "https://api.opensanctions.org/search/default",
        params={"q": query, "limit": "5"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=10.0,
    )
    response.raise_for_status()
    return list(response.json().get("results") or [])[:5]


def run(raw: str, scanner=None) -> ModuleResult:
    query = re.sub(r"\s+", " ", raw).strip()
    if not QUERY.fullmatch(query):
        return ModuleResult(status="failed", error="Enter a person or organization name.")
    scanner = scanner or search_sanctions
    try:
        rows = scanner(query)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"OpenSanctions failed: {exc}")
    findings = [
        Finding("query", query, "opensanctions", "high", f"{len(rows)} public list hits (capped at 5)"),
    ]
    if not rows:
        findings.append(Finding("note", "no hits", "opensanctions", "low", "No matching records in the public index."))
        return ModuleResult(status="ok", findings=findings)
    for row in rows:
        caption = str(row.get("caption") or row.get("id") or "hit")
        schema = str(row.get("schema") or "")
        ident = str(row.get("id") or "")
        findings.append(
            Finding(
                "sanction",
                caption,
                "opensanctions",
                "medium",
                f"{schema} {ident}".strip() + " — list match, not a verdict",
            )
        )
    return ModuleResult(status="ok", findings=findings)
