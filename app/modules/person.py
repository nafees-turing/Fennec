import re

from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.company import _official_website, search_wikidata

NAME = re.compile(r"^[\w .,'-]{2,80}$")
SPEC = ModuleSpec(
    id="person",
    title="Person",
    milestone="later",
    summary="One Wikidata search and at most one entity fetch for a person name.",
    input_label="Full name",
    placeholder="Ada Lovelace",
    available=True,
    network=True,
    category="basic",
)


def run(raw: str, scanner=None) -> ModuleResult:
    value = re.sub(r"\s+", " ", raw).strip()
    if not NAME.fullmatch(value):
        return ModuleResult(status="failed", error="Enter a person name (2–80 characters).")
    scanner = scanner or search_wikidata
    try:
        payload = scanner(value)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Wikidata request failed: {exc}")
    hits = payload.get("hits") or []
    entity = payload.get("entity") or {}
    if not hits:
        return ModuleResult(status="failed", error="Wikidata returned no person for that name.")
    labels = ((entity.get("labels") or {}).get("en") or {}).get("value") or hits[0].get("label") or value
    description = ((entity.get("descriptions") or {}).get("en") or {}).get("value") or hits[0].get("description") or ""
    qid = hits[0].get("id") or ""
    website = _official_website(entity)
    findings = [
        Finding("name", str(labels), "wikidata", "medium", description or "Wikidata search hit"),
    ]
    if qid:
        findings.append(Finding("wikidata", str(qid), "wikidata", "high", "https://www.wikidata.org/wiki/" + str(qid)))
    if website:
        findings.append(Finding("url", website, "wikidata", "medium", "Official website (P856)"))
    return ModuleResult(status="ok", findings=findings)
