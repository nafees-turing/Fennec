import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

SPEC = ModuleSpec(
    id="email",
    title="Email",
    milestone="M3",
    summary="A small Holehe set (about 20 sites), two at a time, so this IP is less likely to get blocked. Set FENNEC_HOLEHE_SITES=all only when you want the full list.",
    input_label="Email address",
    placeholder="name@example.com",
    available=True,
    network=True,
    category="basic",
)

DEFAULT_SITES = {
    "adobe",
    "amazon",
    "discord",
    "docker",
    "flickr",
    "github",
    "google",
    "gravatar",
    "imgur",
    "instagram",
    "office365",
    "patreon",
    "pinterest",
    "protonmail",
    "snapchat",
    "spotify",
    "tumblr",
    "twitter",
    "wordpress",
    "yahoo",
}


def select_sites(websites: list, names: set[str] | None = None) -> list:
    wanted = names if names is not None else DEFAULT_SITES
    if not wanted:
        return list(websites)
    picked = []
    for website in websites:
        if getattr(website, "__name__", "") in wanted:
            picked.append(website)
    return picked


def scan_sites(email: str) -> list[dict]:
    """Run Holehe slowly. Tests replace this function so the suite stays offline."""
    import os

    try:
        import httpx
        import trio
        from holehe.core import get_functions, import_submodules, launch_module
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Missing {exc.name}. Use the project venv: "
            "source .venv/bin/activate && pip install -r requirements.txt && "
            "python -m uvicorn app.main:app --reload"
        ) from exc

    modules = import_submodules("holehe.modules")
    websites = get_functions(modules)
    if os.environ.get("FENNEC_HOLEHE_SITES", "").strip().lower() != "all":
        websites = select_sites(websites)
    out: list[dict] = []
    limit = max(1, int(os.environ.get("FENNEC_NET_CONCURRENCY", "2")))
    delay = max(0.0, float(os.environ.get("FENNEC_NET_DELAY", "0.4")))

    async def _scan() -> list[dict]:
        limiter = trio.CapacityLimiter(limit)
        client = httpx.AsyncClient(timeout=8.0)

        async def one(website) -> None:
            async with limiter:
                await launch_module(website, email, client, out)
                if delay:
                    await trio.sleep(delay)

        try:
            async with trio.open_nursery() as nursery:
                for website in websites:
                    nursery.start_soon(one, website)
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
