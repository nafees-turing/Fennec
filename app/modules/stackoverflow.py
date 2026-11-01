import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="stackoverflow",
    title="Stack Overflow",
    milestone="later",
    summary="One Stack Exchange user search by display name.",
    input_label="Name or handle",
    placeholder="Jon Skeet",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def search_users(query: str) -> list[dict]:
    import httpx

    response = httpx.get(
        "https://api.stackexchange.com/2.3/users",
        params={"order": "desc", "sort": "reputation", "inname": query, "site": "stackoverflow", "pagesize": "3"},
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    return list(response.json().get("items") or [])[:3]


def run(raw: str, scanner=None) -> ModuleResult:
    query = re.sub(r"\s+", " ", raw).strip().lstrip("@")
    if len(query) < 2 or len(query) > 40:
        return ModuleResult(status="failed", error="Enter a display name or handle.")
    scanner = scanner or search_users
    try:
        rows = scanner(query)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Stack Overflow failed: {exc}")
    if not rows:
        return ModuleResult(status="failed", error="No Stack Overflow user matched that name.")
    findings = []
    for row in rows:
        findings.append(
            Finding(
                "username",
                str(row.get("display_name") or query),
                "stackoverflow",
                "medium",
                str(row.get("link") or ""),
            )
        )
        if row.get("location"):
            findings.append(Finding("address", str(row["location"]), "stackoverflow", "low", "Profile location"))
        if row.get("website_url"):
            findings.append(Finding("url", str(row["website_url"]), "stackoverflow", "medium", "Website"))
    return ModuleResult(status="ok", findings=findings)
