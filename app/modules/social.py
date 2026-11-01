import re

from app.modules.base import Finding, ModuleResult, ModuleSpec
from app.modules.profiles import scan

USER = re.compile(r"^[A-Za-z0-9._-]{2,39}$")

SPEC = ModuleSpec(
    id="social",
    title="Social profiles",
    milestone="later",
    summary="Six public social URLs, one after another. Existence only.",
    input_label="Handle",
    placeholder="someone",
    available=True,
    network=True,
    category="social",
)

PROFILES = [
    ("reddit", "https://www.reddit.com/user/{user}"),
    ("youtube", "https://www.youtube.com/@{user}"),
    ("twitch", "https://www.twitch.tv/{user}"),
    ("pinterest", "https://www.pinterest.com/{user}/"),
    ("github", "https://github.com/{user}"),
    ("tiktok", "https://www.tiktok.com/@{user}"),
]


def scan_social(user: str) -> list[dict]:
    return scan(user, PROFILES)


def run(raw: str, scanner=None) -> ModuleResult:
    user = raw.strip()
    if user.startswith("@"):
        user = user[1:]
    if not USER.fullmatch(user):
        return ModuleResult(status="failed", error="Use a short handle (letters, digits, . _ -).")

    scanner = scanner or scan_social
    try:
        rows = scanner(user)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Social scan failed: {exc}")

    hits = [row for row in rows if row.get("exists")]
    unknown = [row for row in rows if not row.get("exists") and row.get("status") not in {404, 410}]
    findings = [
        Finding(
            "username",
            user,
            "fennec",
            "high",
            f"{len(hits)} social hits, {len(unknown)} unclear, {len(rows)} checked",
        )
    ]
    for row in hits:
        findings.append(
            Finding(
                "account",
                str(row.get("url") or row.get("name")),
                row.get("name") or "social",
                "medium",
                f"HTTP {row.get('status')} on a public profile URL",
            )
        )
    for row in unknown:
        note = str(row.get("error") or f"HTTP {row.get('status')}; not treated as a confirmed profile")
        findings.append(Finding("rate_limit", str(row.get("name")), "fennec", "low", note))
    return ModuleResult(status="ok", findings=findings)
