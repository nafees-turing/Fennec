import re

from app.modules.base import Finding, ModuleResult, ModuleSpec

NAME = re.compile(r"^[\w .,'-]{2,80}$")

SPEC = ModuleSpec(
    id="name",
    title="Name",
    milestone="later",
    summary="Attach a person name to the case. No lookup.",
    input_label="Full name",
    placeholder="Ada Lovelace",
    available=True,
    network=False,
    category="basic",
)


def run(raw: str) -> ModuleResult:
    value = re.sub(r"\s+", " ", raw).strip()
    if not NAME.fullmatch(value):
        return ModuleResult(status="failed", error="Enter a person name (2–80 characters).")
    return ModuleResult(
        status="ok",
        findings=[Finding("name", value, "fennec", "high", "Recorded on the case. Not a registry search.")],
    )
