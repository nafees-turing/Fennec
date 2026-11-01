import phonenumbers
from phonenumbers import carrier, geocoder, timezone

from app.modules.base import Finding, ModuleResult, ModuleSpec

SPEC = ModuleSpec(
    id="phone",
    title="Phone",
    milestone="M5",
    summary="Public numbering-plan metadata. No subscriber lookup.",
    input_label="Number in international format",
    placeholder="+14155552671",
    available=True,
    network=False,
)


def run(raw: str) -> ModuleResult:
    text = raw.strip()
    try:
        number = phonenumbers.parse(text, None)
    except phonenumbers.NumberParseException as exc:
        return ModuleResult(status="failed", error=f"Could not parse number: {exc}")

    if not phonenumbers.is_possible_number(number):
        return ModuleResult(status="failed", error="Number is not possible for its country code.")

    formatted = phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    region = geocoder.description_for_number(number, "en") or ""
    carrier_name = carrier.name_for_number(number, "en") or ""
    zones = list(timezone.time_zones_for_number(number))
    valid = phonenumbers.is_valid_number(number)
    evidence = (
        f"valid={valid}; possible=true; "
        f"country_code=+{number.country_code}; "
        "carrier is the original prefix owner, not a live location"
    )
    findings = [
        Finding("phone", formatted, "phonenumbers", "high" if valid else "medium", evidence),
    ]
    if region:
        findings.append(Finding("region", region, "phonenumbers", "medium", "Numbering-plan region, not GPS."))
    if carrier_name:
        findings.append(
            Finding("carrier", carrier_name, "phonenumbers", "low", "Original range owner. Ported numbers can differ.")
        )
    if zones:
        findings.append(Finding("timezone", ", ".join(zones), "phonenumbers", "medium", "Time zones for the number range."))
    return ModuleResult(status="ok", findings=findings)
