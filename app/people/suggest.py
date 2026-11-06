from app.people.profiles import _from_query, anchor_keys, similar_handle


def attached_profile(query: str, profiles: list[dict]) -> dict | None:
    keys = set(_from_query(query))
    if not keys:
        return None
    for profile in profiles:
        if keys & set(anchor_keys(profile)):
            return profile
    return None


def candidates(query: str, profiles: list[dict], limit: int = 5) -> list[dict]:
    if attached_profile(query, profiles):
        return []
    keys = _from_query(query)
    handles = [key.split(":", 1)[1] for key in keys if key.startswith("username:")]
    names = [key.split(":", 1)[1] for key in keys if key.startswith("name:")]
    emails = [key.split(":", 1)[1] for key in keys if key.startswith("email:")]
    locals_ = [item.split("@", 1)[0] for item in emails]
    out = []
    for profile in profiles:
        score = 0
        reasons = []
        for handle in handles + locals_:
            for username in profile.get("usernames") or []:
                if similar_handle(handle, username.lower()):
                    score += 2
                    reasons.append(f"similar handle {username}")
            for email in profile.get("emails") or []:
                local = email.split("@", 1)[0].lower()
                if similar_handle(handle, local):
                    score += 2
                    reasons.append(f"similar to {email}")
        for name in names:
            for existing in profile.get("names") or []:
                if similar_handle(name.replace(" ", ""), existing.lower().replace(" ", "")):
                    score += 3
                    reasons.append(f"similar name {existing}")
        if score:
            out.append(
                {
                    "id": profile["id"],
                    "title": profile["title"],
                    "score": score,
                    "reasons": list(dict.fromkeys(reasons))[:4],
                }
            )
    out.sort(key=lambda item: (-item["score"], item["title"].lower()))
    return out[:limit]
