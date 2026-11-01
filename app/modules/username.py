import re

from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.profiles import scan

USER = re.compile(r"^[A-Za-z0-9._-]{2,39}$")

SPEC = ModuleSpec(
    id="username",
    title="Username",
    milestone="M2",
    summary="Eight public profile URLs, one after another. Not a full Maigret sweep.",
    input_label="Username",
    placeholder="someone",
    available=True,
    network=True,
    category="basic",
)

PROFILES = [
    ("github", "https://github.com/{user}"),
    ("gitlab", "https://gitlab.com/{user}"),
    ("codeberg", "https://codeberg.org/{user}"),
    ("reddit", "https://www.reddit.com/user/{user}"),
    ("hackernews", "https://news.ycombinator.com/user?id={user}"),
    ("keybase", "https://keybase.io/{user}"),
    ("sourceforge", "https://sourceforge.net/u/{user}/profile"),
    ("pypi", "https://pypi.org/user/{user}/"),
]


def scan_username(user: str) -> list[dict]:
    return scan(user, PROFILES)


def run(raw: str, scanner=None) -> ModuleResult:
    user = raw.strip()
    if user.startswith("@"):
        user = user[1:]
    if not USER.fullmatch(user):
        return ModuleResult(status="failed", error="Use a short username (letters, digits, . _ -).")

    scanner = scanner or scan_username
    try:
        rows = scanner(user)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Username scan failed: {exc}")

    hits = [row for row in rows if row.get("exists")]
    unknown = [row for row in rows if not row.get("exists") and row.get("status") not in {404, 410}]
    findings = [
        Finding(
            "username",
            user,
            "fennec",
            "high",
            f"{len(hits)} profiles, {len(unknown)} unclear, {len(rows)} checked",
        )
    ]
    for row in hits:
        findings.append(
            Finding(
                "account",
                str(row.get("url") or row.get("name")),
                row.get("name") or "profile",
                "medium",
                f"HTTP {row.get('status')} on a public profile URL",
            )
        )
    for row in unknown:
        if row.get("error"):
            findings.append(
                Finding("rate_limit", str(row.get("name")), "fennec", "low", str(row.get("error")))
            )
        elif row.get("status"):
            findings.append(
                Finding(
                    "rate_limit",
                    str(row.get("name")),
                    "fennec",
                    "low",
                    f"HTTP {row.get('status')}; not treated as a confirmed profile",
                )
            )
    return ModuleResult(status="ok", findings=findings)
