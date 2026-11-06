import re

from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.profiles import probe

SLUG = re.compile(r"^[A-Za-z0-9_-]{3,100}$")
SPEC = ModuleSpec(
    id="linkedin",
    title="LinkedIn",
    milestone="later",
    summary="One public GET of linkedin.com/in/slug. LinkedIn usually blocks anonymous checks; 403 is not a hit.",
    input_label="LinkedIn public slug",
    placeholder="first-last",
    available=True,
    network=True,
    category="social",
)


def fetch_profile(slug: str) -> dict:
    return probe(f"https://www.linkedin.com/in/{slug}/")


def run(raw: str, scanner=None) -> ModuleResult:
    slug = raw.strip().lstrip("@").rstrip("/")
    if "linkedin.com/in/" in slug.lower():
        slug = slug.split("linkedin.com/in/", 1)[1].strip("/")
    if not SLUG.fullmatch(slug):
        return ModuleResult(status="failed", error="Enter a public LinkedIn slug (the /in/ name).")
    scanner = scanner or fetch_profile
    try:
        row = scanner(slug)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"LinkedIn lookup failed: {exc}")
    findings = [Finding("username", slug, "linkedin", "medium", "Public /in/ URL check. No login, no scrape.")]
    if row.get("exists") and row.get("url"):
        findings.append(
            Finding("account", str(row["url"]), "linkedin", "medium", f"HTTP {row.get('status')} on a public URL")
        )
    return ModuleResult(status="ok", findings=findings)
