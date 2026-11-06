import hashlib
import re
from collections import defaultdict
from difflib import SequenceMatcher
from urllib.parse import urlparse

from app.detect import classify
from app.people.keep import PERSON_MODULES, is_relevant

SKIP = {
    "rate_limit",
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
}
IDENTITY = {"email", "phone", "username", "name", "wikidata", "wallet"}
PHONE_DIGITS = re.compile(r"\D+")
NOISE_VALUE = re.compile(r"^(none|missing|no match|no hits|not in community index|no published key|no snapshot)", re.I)


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, item: str) -> None:
        self.parent.setdefault(item, item)

    def find(self, item: str) -> str:
        self.add(item)
        if self.parent[item] != item:
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[b] = a


def _norm_phone(value: str) -> str:
    return PHONE_DIGITS.sub("", value)


def identity_keys(kind: str, value: str) -> list[str]:
    text = value.strip()
    if not text or NOISE_VALUE.search(text):
        return []
    lowered = text.lower()
    if kind == "phone":
        digits = _norm_phone(text)
        return [f"phone:{digits}"] if len(digits) >= 8 else []
    if kind == "email":
        keys = [f"email:{lowered}"]
        local = lowered.split("@", 1)[0]
        if len(local) >= 3:
            keys.append(f"username:{local}")
        return keys
    if kind == "username":
        return [f"username:{lowered.lstrip('@')}"]
    if kind == "name":
        return [f"name:{re.sub(r'\s+', ' ', lowered)}"]
    if kind == "wikidata":
        return [f"wikidata:{text.upper()}"]
    if kind == "wallet":
        return [f"wallet:{text}"]
    if kind == "account":
        if "://" in text:
            parsed = urlparse(text)
            path = (parsed.path or "").strip("/")
            if path:
                return [f"account:{text.lower().rstrip('/')}"]
        return []
    return []


def _from_query(query: str) -> list[str]:
    classified = classify(query)
    kind = classified.get("detected")
    if not kind:
        return []
    value = query.strip()
    if kind == "username":
        value = value.lstrip("@")
    mapping = {
        "email": "email",
        "phone": "phone",
        "username": "username",
        "name": "name",
        "bitcoin": "wallet",
        "ethereum": "wallet",
    }
    slot = mapping.get(kind)
    if not slot:
        return []
    return identity_keys(slot, value)


def build(findings: list[dict], lookups: list[dict] | None = None, unions: list[tuple[str, str]] | None = None) -> list[dict]:
    uf = UnionFind()
    finding_ids: dict[str, list[int]] = defaultdict(list)

    def attach(keys: list[str], finding_id: int | None = None) -> None:
        if not keys:
            return
        root_key = keys[0]
        uf.add(root_key)
        for key in keys[1:]:
            uf.union(root_key, key)
        if finding_id is not None:
            finding_ids[uf.find(root_key)].append(finding_id)

    run_module: dict[int, str] = {}
    if lookups:
        for lookup in lookups:
            for run in lookup.get("runs") or []:
                if run.get("id") is not None:
                    run_module[int(run["id"])] = str(run.get("module_id") or "")

    run_keys: dict[int, list[str]] = defaultdict(list)
    for row in findings:
        kind = str(row.get("kind") or "")
        value = str(row.get("value") or "")
        if not is_relevant(kind, value, str(row.get("evidence") or "")):
            continue
        if kind in SKIP:
            continue
        keys = identity_keys(kind, value)
        if not keys:
            continue
        run_id = row.get("run_id")
        if run_id is not None:
            run_keys[int(run_id)].extend(keys)
        attach(keys, row.get("id"))

    for run_id, keys in run_keys.items():
        unique = list(dict.fromkeys(keys))
        if len(unique) > 1:
            for key in unique[1:]:
                uf.union(unique[0], key)

    if lookups:
        for lookup in lookups:
            query_keys = _from_query(str(lookup.get("query") or ""))
            related: list[str] = list(query_keys)
            for run in lookup.get("runs") or []:
                related.extend(run_keys.get(int(run.get("id") or 0), []))
            related = list(dict.fromkeys(related))
            if related:
                attach(related)

    extra: list[dict] = []
    if lookups:
        for lookup in lookups:
            query = str(lookup.get("query") or "")
            detected = classify(query).get("detected")
            if detected in {"ip", "domain", "bitcoin", "ethereum"}:
                continue
            has_hit = False
            for run in lookup.get("runs") or []:
                if str(run.get("module_id") or "") not in PERSON_MODULES:
                    continue
                if run.get("status") == "ok" and run.get("findings"):
                    has_hit = True
                    break
            qkeys = _from_query(query)
            if not qkeys or not has_hit:
                continue
            kind = {
                "email": "email",
                "phone": "phone",
                "username": "username",
                "name": "name",
            }.get(detected or "", "")
            if kind:
                attach(qkeys, None)
                extra.append(
                    {
                        "id": None,
                        "run_id": None,
                        "kind": kind,
                        "value": query.lstrip("@") if kind == "username" else query,
                    }
                )

    merge_similar(uf)
    for left, right in unions or []:
        if left and right:
            uf.union(left, right)

    buckets: dict[str, list[dict]] = defaultdict(list)
    for row in list(findings) + extra:
        kind = str(row.get("kind") or "")
        value = str(row.get("value") or "").strip()
        if not is_relevant(kind, value, str(row.get("evidence") or "")):
            continue
        if kind in SKIP or not value or NOISE_VALUE.search(value):
            continue
        module_id = run_module.get(int(row["run_id"])) if row.get("run_id") is not None else ""
        if module_id and module_id not in PERSON_MODULES and kind not in {"email", "phone", "username", "name", "account", "url"}:
            continue
        keys = identity_keys(kind, value)
        run_id = row.get("run_id")
        if not keys and run_id in run_keys and run_keys[run_id]:
            keys = [run_keys[run_id][0]]
        if not keys and module_id in PERSON_MODULES and row.get("run_id") is not None:
            for lookup in lookups or []:
                for run in lookup.get("runs") or []:
                    if run.get("id") == row.get("run_id"):
                        qkeys = _from_query(str(lookup.get("query") or ""))
                        if qkeys:
                            keys = qkeys
                        break
        if not keys:
            continue
        buckets[uf.find(keys[0])].append(row)

    profiles = []
    for index, rows in enumerate(buckets.values(), start=1):
        slots: dict[str, list[str]] = defaultdict(list)

        def put(slot: str, value: str) -> None:
            text = value.strip()
            if not text or text in slots[slot]:
                return
            slots[slot].append(text)

        for row in rows:
            kind = row["kind"]
            value = str(row["value"])
            if kind in {"email", "phone", "username", "name", "address", "company", "url", "wallet", "account"}:
                put(kind if kind != "account" else "accounts", value)
            elif kind == "wikidata":
                put("wikidata", value)
            elif kind in {"country", "region", "place", "coords"}:
                put("places", value)
            else:
                put("other", f"{kind}: {value}")
        title = (
            (slots["name"] or [None])[0]
            or (slots["username"] or [None])[0]
            or (slots["email"] or [None])[0]
            or (slots["phone"] or [None])[0]
            or f"Profile {index}"
        )
        avatar_url = None
        if slots["email"]:
            digest = hashlib.md5(slots["email"][0].lower().encode("utf-8")).hexdigest()
            avatar_url = f"https://www.gravatar.com/avatar/{digest}?s=128&d=identicon"
        profiles.append(
            {
                "id": index,
                "title": title,
                "avatar_url": avatar_url,
                "names": slots["name"],
                "emails": slots["email"],
                "phones": slots["phone"],
                "usernames": slots["username"],
                "accounts": slots["accounts"],
                "addresses": slots["address"],
                "companies": slots["company"],
                "urls": slots["url"],
                "wallets": slots["wallet"],
                "places": slots["places"],
                "wikidata": slots["wikidata"],
                "other": slots["other"][:12],
                "finding_count": len(rows),
                "finding_ids": [row["id"] for row in rows if row.get("id") is not None],
                "map_url": _map_url(slots["places"]),
                "notes": "",
            }
        )
    profiles.sort(key=lambda item: (-item["finding_count"], item["title"].lower()))
    for index, profile in enumerate(profiles, start=1):
        profile["id"] = index
    return profiles


def _map_url(places: list[str]) -> str | None:
    for item in places:
        parts = str(item).split(",")
        if len(parts) < 2:
            continue
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}#map=12/{lat}/{lon}"
    return None


def similar_handle(left: str, right: str) -> bool:
    if left == right:
        return True
    short, long_ = (left, right) if len(left) <= len(right) else (right, left)
    if len(short) >= 4 and (long_.startswith(short) or short in long_ and len(long_) - len(short) <= 5):
        return True
    return min(len(left), len(right)) >= 4 and SequenceMatcher(None, left, right).ratio() >= 0.82


def merge_similar(uf: UnionFind) -> None:
    handles = [key for key in list(uf.parent) if key.startswith("username:")]
    for i, left in enumerate(handles):
        a = left.split(":", 1)[1]
        for right in handles[i + 1 :]:
            b = right.split(":", 1)[1]
            if similar_handle(a, b):
                uf.union(left, right)
    names = [key for key in list(uf.parent) if key.startswith("name:")]
    for i, left in enumerate(names):
        a = left.split(":", 1)[1]
        for right in names[i + 1 :]:
            b = right.split(":", 1)[1]
            if similar_handle(a.replace(" ", ""), b.replace(" ", "")) or a in b or b in a:
                uf.union(left, right)


def anchor_keys(profile: dict) -> list[str]:
    keys: list[str] = []
    for kind, slot in (
        ("email", "emails"),
        ("phone", "phones"),
        ("username", "usernames"),
        ("name", "names"),
        ("wallet", "wallets"),
        ("wikidata", "wikidata"),
    ):
        for value in profile.get(slot) or []:
            keys.extend(identity_keys(kind, str(value)))
    return list(dict.fromkeys(keys))

