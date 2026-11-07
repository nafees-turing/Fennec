import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

USER = re.compile(r"^[A-Za-z0-9_]{2,32}$")
SPEC = ModuleSpec(
    id="steam",
    title="Steam",
    milestone="later",
    summary="One public Steam community profile page. No API key.",
    input_label="Steam vanity name",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_profile(login: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://steamcommunity.com/id/{login}/",
        params={"xml": "1"},
        headers={"User-Agent": USER_AGENT, "Accept": "text/xml,text/plain"},
        timeout=8.0,
        follow_redirects=True,
    )
    if response.status_code >= 400:
        return {"found": False}
    text = response.text
    if "<steamID>" not in text and "The specified profile could not be found" in text:
        return {"found": False}
    name = ""
    if "<steamID><![CDATA[" in text:
        name = text.split("<steamID><![CDATA[", 1)[1].split("]]>", 1)[0].strip()
    return {"found": "<steamID>" in text, "name": name, "url": f"https://steamcommunity.com/id/{login}/"}


def run(raw: str, scanner=None) -> ModuleResult:
    login = raw.strip().lstrip("@")
    if not USER.fullmatch(login):
        return ModuleResult(status="failed", error="Enter a Steam vanity name.")
    scanner = scanner or fetch_profile
    try:
        data = scanner(login)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Steam lookup failed: {exc}")
    findings = [Finding("username", login, "steam", "medium", "Public vanity URL only.")]
    if data.get("found"):
        findings.append(
            Finding("account", data.get("url") or f"https://steamcommunity.com/id/{login}/", "steam", "medium", "Public profile")
        )
        if data.get("name"):
            findings.append(Finding("name", str(data["name"]), "steam", "medium", "Steam display name"))
    return ModuleResult(status="ok", findings=findings)
