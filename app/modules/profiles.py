import os
import time


def probe(url: str) -> dict:
    import httpx

    headers = {"User-Agent": "Fennec-local-osint/0.1"}
    try:
        response = httpx.head(url, follow_redirects=True, timeout=8.0, headers=headers)
        if response.status_code in {403, 405, 501}:
            response = httpx.get(url, follow_redirects=True, timeout=8.0, headers=headers)
    except Exception as exc:
        return {"url": url, "status": 0, "exists": False, "error": str(exc)}
    return {
        "url": str(response.url),
        "status": response.status_code,
        "exists": response.status_code == 200,
        "error": None,
    }


def scan(user: str, templates: list[tuple[str, str]]) -> list[dict]:
    delay = max(0.0, float(os.environ.get("FENNEC_NET_DELAY", "0.5")))
    rows = []
    for name, template in templates:
        row = probe(template.format(user=user))
        row["name"] = name
        rows.append(row)
        if delay:
            time.sleep(delay)
    return rows
