import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

SPEC = ModuleSpec(
    id="email",
    title="Email",
    milestone="M3",
    summary="Sites where this address appears registered. Holehe checks 120+ services from this machine.",
    input_label="Email address",
    placeholder="name@example.com",
    available=True,
)


def scan_sites(email: str) -> list[dict]:
    """Run Holehe. Tests replace this function so the suite stays offline."""
    import httpx
    import trio
    from holehe.core import get_functions, import_submodules, launch_module

    modules = import_submodules("holehe.modules")
    websites = get_functions(modules)
    out: list[dict] = []

    async def _scan() -> list[dict]:
        client = httpx.AsyncClient(timeout=10.0)
        try:
            async with trio.open_nursery() as nursery:
                for website in websites:
                    nursery.start_soon(launch_module, website, email, client, out)
        finally:
            await client.aclose()
        return sorted(out, key=lambda row: str(row.get("name") or ""))

    return trio.run(_scan)


def run(raw: str, scanner=None) -> ModuleResult:
    email = raw.strip().lower()
    if not EMAIL.fullmatch(email):
        return ModuleResult(status="failed", error="Enter a single email address.")

    scanner = scanner or scan_sites
    try:
        rows = scanner(email)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Holehe failed: {exc}")

    registered = [row for row in rows if row.get("exists") is True]
    limited = [row for row in rows if row.get("rateLimit") is True]
    findings = [
        Finding(
            "email",
            email,
            "holehe",
            "high",
            f"{len(registered)} registered, {len(limited)} rate-limited, {len(rows)} checked",
        )
    ]
    for row in registered:
        domain = str(row.get("domain") or row.get("name") or "")
        extra = []
        if row.get("emailrecovery"):
            extra.append(f"recovery={row['emailrecovery']}")
        if row.get("phoneNumber"):
            extra.append(f"hint={row['phoneNumber']}")
        if row.get("others"):
            extra.append(str(row["others"]))
        findings.append(
            Finding(
                "account",
                domain,
                "holehe",
                "high",
                extra and "; ".join(extra) or "Site reports this email is registered.",
            )
        )
    for row in limited:
        domain = str(row.get("domain") or row.get("name") or "")
        findings.append(
            Finding("rate_limit", domain, "holehe", "low", "Site rate-limited the check.")
        )
    return ModuleResult(status="ok", findings=findings)
