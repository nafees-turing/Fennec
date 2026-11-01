import re
from collections import defaultdict
from urllib.parse import urlparse

PHONE_DIGITS = re.compile(r"\D+")


def _host(value: str) -> str:
    text = value.strip().lower()
    if "://" in text:
        host = urlparse(text).hostname or ""
    else:
        host = text.split("/")[0]
    if host.startswith("www."):
        host = host[4:]
    return host.strip(".")


def keys_for(finding: dict) -> list[tuple[str, str]]:
    kind = str(finding.get("kind") or "")
    value = str(finding.get("value") or "").strip().lower()
    if not value:
        return []
    keys = [(kind, value)]
    if kind == "email" and "@" in value:
        keys.append(("domain", value.split("@", 1)[1]))
    elif kind in {"domain", "nameserver", "mx"}:
        host = _host(value.split()[-1])
        if host:
            keys.append(("domain", host))
    elif kind == "phone":
        keys.append(("phone", PHONE_DIGITS.sub("", value)))
    elif kind == "account":
        host = _host(value)
        if host:
            keys.append(("url", value if "://" in value else host))
    return keys


def links(findings: list[dict]) -> list[dict]:
    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for finding in findings:
        seen = set()
        for key in keys_for(finding):
            if key in seen:
                continue
            seen.add(key)
            buckets[key].append(finding)
    out = []
    for (kind, value), rows in buckets.items():
        ids = sorted({row["id"] for row in rows if "id" in row})
        if len(ids) < 2:
            continue
        out.append(
            {
                "kind": kind,
                "value": value,
                "finding_ids": ids,
                "count": len(ids),
            }
        )
    out.sort(key=lambda item: (-item["count"], item["kind"], item["value"]))
    return out
