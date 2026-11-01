import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="address",
    title="Address",
    milestone="later",
    summary="Attach a postal or location line to the case. No geocoding API.",
    input_label="Street or place",
    placeholder="221B Baker Street, London",
    available=True,
    network=False,
    category="addresses",
)


def run(raw: str) -> ModuleResult:
    value = re.sub(r"\s+", " ", raw).strip()
    if len(value) < 5 or len(value) > 200:
        return ModuleResult(status="failed", error="Enter a short postal or location line.")
    return ModuleResult(
        status="ok",
        findings=[Finding("address", value, "fennec", "high", "Recorded on the case. Not a live map pin.")],
    )
