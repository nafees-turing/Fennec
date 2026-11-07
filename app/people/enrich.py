"""Run extra public lookups from identifiers already on a person profile."""

SETS = {
    "social": {
        "label": "Find social",
        "seed": "username",
        "modules": [
            "social",
            "twitter",
            "linkedin",
            "github",
            "gitlab",
            "keybase",
            "reddit",
            "devto",
            "steam",
            "roblox",
        ],
    },
    "email": {
        "label": "Find email",
        "seed": "email",
        "modules": ["email", "gravatar", "pgp"],
    },
    "name": {
        "label": "Find name",
        "seed": "name",
        "modules": ["person", "wikipedia", "stackoverflow", "sanctions"],
    },
    "phone": {
        "label": "Find phone",
        "seed": "phone",
        "modules": ["phone"],
    },
}


def seed_value(profile: dict, kind: str) -> str | None:
    mapping = {
        "username": profile.get("usernames") or [],
        "email": profile.get("emails") or [],
        "name": profile.get("names") or [profile.get("title")] or [],
        "phone": profile.get("phones") or [],
    }
    for value in mapping.get(kind) or []:
        text = str(value or "").strip()
        if text:
            return text
    return None


def available_actions(profile: dict) -> list[dict]:
    out = []
    for key, spec in SETS.items():
        value = seed_value(profile, spec["seed"])
        if value:
            out.append({"id": key, "label": spec["label"], "value": value})
    return out
