from app.modules.base import ModuleResult, ModuleSpec
from app.modules import company, domain, email, geoip, metadata, phone, username

_SPECS = {
    item.id: item
    for item in [
        email.SPEC,
        phone.SPEC,
        domain.SPEC,
        username.SPEC,
        company.SPEC,
        geoip.SPEC,
        metadata.SPEC,
    ]
}
_RUNNERS = {
    "email": email.run,
    "phone": phone.run,
    "domain": domain.run,
    "username": username.run,
    "company": company.run,
    "geoip": geoip.run,
    "metadata": metadata.run,
}


def list_modules() -> list[ModuleSpec]:
    return list(_SPECS.values())


def get_module(module_id: str) -> ModuleSpec | None:
    return _SPECS.get(module_id)


def execute(module_id: str, value: str) -> ModuleResult:
    spec = _SPECS[module_id]
    if not spec.available:
        raise RuntimeError(spec.reason)
    return _RUNNERS[module_id](value)
