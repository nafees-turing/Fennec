"""Operator title, notes, and primary contact for a profile, keyed by an identity anchor."""

from app.people.profiles import anchor_keys


def apply_edits(profiles: list[dict], edits: list[dict]) -> list[dict]:
    by_anchor = {str(row["anchor"]): row for row in edits}
    for profile in profiles:

        hit = None
        for key in anchor_keys(profile):
            if key in by_anchor:
                hit = by_anchor[key]
                break
        if not hit:
            continue
        if hit.get("title"):
            profile["title"] = str(hit["title"])
        if hit.get("notes") is not None:
            profile["notes"] = str(hit["notes"])
        if hit.get("primary_email"):
            profile["primary_email"] = str(hit["primary_email"])
            emails = profile.get("emails") or []
            if hit["primary_email"] in emails:
                profile["emails"] = [hit["primary_email"]] + [item for item in emails if item != hit["primary_email"]]
        if hit.get("primary_phone"):
            profile["primary_phone"] = str(hit["primary_phone"])
            phones = profile.get("phones") or []
            if hit["primary_phone"] in phones:
                profile["phones"] = [hit["primary_phone"]] + [item for item in phones if item != hit["primary_phone"]]
        profile["edit_anchor"] = hit["anchor"]
    return profiles
