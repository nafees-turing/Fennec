import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

BTC = re.compile(r"^(bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$")
SPEC = ModuleSpec(
    id="bitcoin",
    title="Bitcoin",
    milestone="later",
    summary="One mempool.space address lookup. Balance and tx count only.",
    input_label="Bitcoin address",
    placeholder="bc1q...",
    available=True,
    network=True,
    category="crypto",
)

USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_address(addr: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://mempool.space/api/address/{addr}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    addr = raw.strip()
    if not BTC.fullmatch(addr):
        return ModuleResult(status="failed", error="Enter a Bitcoin address (1…, 3…, or bc1…).")
    scanner = scanner or fetch_address
    try:
        data = scanner(addr)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"mempool.space failed: {exc}")
    chain = data.get("chain_stats") or {}
    funded = int(chain.get("funded_txo_sum") or 0)
    spent = int(chain.get("spent_txo_sum") or 0)
    balance = funded - spent
    findings = [
        Finding("wallet", addr, "mempool.space", "high", "Bitcoin address"),
        Finding("balance", f"{balance} sat", "mempool.space", "medium", f"funded={funded} spent={spent}"),
        Finding("tx_count", str(chain.get("tx_count") or 0), "mempool.space", "medium", "Confirmed transactions"),
    ]
    return ModuleResult(status="ok", findings=findings)
