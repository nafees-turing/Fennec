import re

DROP_KINDS = {
    "rate_limit",
    "note",
    "query",
    "scope",
    "line_type",
    "timezone",
    "noise",
    "cert_name",
    "prefix",
    "port",
    "software",
    "cve",
    "rir",
    "tx_count",
    "txt",
    "status",
    "created",
    "expires",
    "updated",
    "nameserver",
    "mx",
    "balance",
}

NOISE = re.compile(
    r"^(none|missing|no match|no hits|not in community|no published|no snapshot|no location)",
    re.I,
)

KEEP_KINDS = {
    "email",
    "phone",
    "name",
    "username",
    "account",
    "address",
    "company",
    "sanction",
    "url",
    "wallet",
    "wikidata",
    "country",
    "region",
    "city",
    "coords",
    "place",
    "ip",
    "ipv6",
    "domain",
    "asn",
    "org",
    "file",
    "hash",
    "format",
    "exif",
    "gps",
    "hostname",
    "carrier",
    "registrar",
    "registrant",
}

PERSON_MODULES = {
    "email",
    "name",
    "person",
    "username",
    "phone",
    "social",
    "github",
    "gitlab",
    "keybase",
    "gravatar",
    "pgp",
    "wikipedia",
    "reddit",
    "npm",
    "dockerhub",
    "hackernews",
    "chess",
    "lichess",
    "stackoverflow",
    "devto",
    "company",
    "sanctions",
    "address",
    "geocode",
}


def is_relevant(kind: str, value: str, evidence: str = "") -> bool:
    kind = (kind or "").strip()
    value = (value or "").strip()
    if not kind or not value:
        return False
    if kind in DROP_KINDS:
        return False
    if kind not in KEEP_KINDS:
        return False
    if NOISE.search(value):
        return False
    if kind == "account" and value.lower() in {"gravatar", "(none)"}:
        return False
    if kind == "hostname" and ("." not in value or value.lower() in {"(none)", "none"}):
        return False
    return True


def filter_findings(rows: list[dict]) -> list[dict]:
    kept = []
    for row in rows:
        if is_relevant(str(row.get("kind") or ""), str(row.get("value") or ""), str(row.get("evidence") or "")):
            kept.append(row)
    return kept
