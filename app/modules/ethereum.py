import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

ETH = re.compile(r"^0x[a-fA-F0-9]{40}$")
SPEC = ModuleSpec(
    id="ethereum",
    title="Ethereum",
    milestone="later",
    summary="One Blockscout address lookup. No API key.",
    input_label="Ethereum address",
    placeholder="0x...",
    available=True,
    network=True,
    category="crypto",
)
USER_AGENT = "Fennec/0.1 (local OSINT workbench; https://github.com/nafees-turing/Fennec)"


def fetch_address(addr: str) -> dict:
    import httpx

    response = httpx.get(
        f"https://eth.blockscout.com/api/v2/addresses/{addr}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=8.0,
    )
    response.raise_for_status()
    return response.json()


def run(raw: str, scanner=None) -> ModuleResult:
    addr = raw.strip()
    if not ETH.fullmatch(addr):
        return ModuleResult(status="failed", error="Enter an Ethereum address (0x plus 40 hex digits).")
    scanner = scanner or fetch_address
    try:
        data = scanner(addr)
    except Exception as exc:
        return ModuleResult(status="failed", error=f"Blockscout failed: {exc}")
    findings = [Finding("wallet", addr, "blockscout", "high", "Ethereum address")]
    if data.get("name"):
        findings.append(Finding("name", str(data["name"]), "blockscout", "medium", "Public name tag"))
    coin = data.get("coin_balance")
    if coin is not None:
        findings.append(Finding("balance", str(coin), "blockscout", "medium", "Wei, from Blockscout"))
    if data.get("is_contract"):
        findings.append(Finding("note", "contract", "blockscout", "medium", "Address is a contract"))
    return ModuleResult(status="ok", findings=findings)
