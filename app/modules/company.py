import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

NAME = re.compile(r"^[\w .,&'()-]{2,80}$")
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"

SPEC = ModuleSpec(
    id="company",
    title="Company",
    milestone="later",
    summary="One Wikidata search and at most one entity fetch. No bulk scrape.",
    input_label="Company or organization name",
    placeholder="Example Ltd",
    available=True,
    network=True,
    category="addresses",
)


def search_wikidata(name: str) -> dict:
    import httpx

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    with httpx.Client(timeout=8.0, headers=headers) as client:
        search = client.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action": "wbsearchentities",
                "search": name,
                "language": "en",
                "format": "json",
                "limit": "3",
                "type": "item",
            },
        )
        search.raise_for_status()
        hits = search.json().get("search") or []
        entity = {}
        if hits:
            qid = hits[0].get("id")
            detail = client.get(
                f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
            )
            detail.raise_for_status()
            entity = (detail.json().get("entities") or {}).get(qid) or {}
        return {"hits": hits, "entity": entity}


def _claim_id(entity: dict, prop: str) -> str:
    claims = (entity.get("claims") or {}).get(prop) or []
    if not claims:
        return ""
    mainsnak = claims[0].get("mainsnak") or {}
    datavalue = mainsnak.get("datavalue") or {}
    value = datavalue.get("value")
    if isinstance(value, dict):
        return str(value.get("id") or value.get("text") or "")
    return str(value or "")


def _official_website(entity: dict) -> str:
    claims = (entity.get("claims") or {}).get("P856") or []
    if not claims:
        return ""
    value = ((claims[0].get("mainsnak") or {}).get("datavalue") or {}).get("value")
    return str(value or "")


def run(raw: str, scanner=None) -> ModuleResult:
    name = re.sub(r"\s+", " ", raw).strip()
    if not NAME.fullmatch(name):
        return ModuleResult(status="failed", error="Enter an organization name (2–80 characters).")

    scanner = scanner or search_wikidata
    try:
        payload = scanner(name)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Wikidata request failed: {exc}")

    hits = payload.get("hits") or []
    entity = payload.get("entity") or {}
    if not hits:
        return ModuleResult(status="failed", error="Wikidata returned no organization for that name.")

    labels = ((entity.get("labels") or {}).get("en") or {}).get("value") or hits[0].get("label") or name
    description = ((entity.get("descriptions") or {}).get("en") or {}).get("value") or hits[0].get("description") or ""
    qid = hits[0].get("id") or ""
    website = _official_website(entity)
    findings = [
        Finding("company", str(labels), "wikidata", "medium", description or "Wikidata search hit"),
    ]
    if qid:
        findings.append(Finding("wikidata", str(qid), "wikidata", "high", "https://www.wikidata.org/wiki/" + str(qid)))
    if website:
        findings.append(Finding("url", website, "wikidata", "medium", "Official website (P856)"))
    for extra in hits[1:]:
        findings.append(
            Finding(
                "company",
                str(extra.get("label") or extra.get("id")),
                "wikidata",
                "low",
                extra.get("description") or "Additional search hit; not fetched",
            )
        )
    return ModuleResult(status="ok", findings=findings)
