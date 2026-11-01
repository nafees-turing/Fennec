from app.modules.base import ModuleResult, ModuleSpec
from app.modules import (
    address,
    archive,
    certs,
    company,
    domain,
    email,
    geoip,
    metadata,
    name,
    phone,
    social,
    username,
)

CATEGORIES = [
    ("basic", "Basic"),
    ("social", "Social"),
    ("addresses", "Addresses"),
    ("network", "Network"),
    ("files", "Files"),
]

_SPECS = {
    item.id: item
    for item in [
        email.SPEC,
        name.SPEC,
        username.SPEC,
        phone.SPEC,
        social.SPEC,
        address.SPEC,
        company.SPEC,
        domain.SPEC,
        geoip.SPEC,
        certs.SPEC,
        archive.SPEC,
        metadata.SPEC,
    ]
}
_RUNNERS = {
    "email": email.run,
    "name": name.run,
    "username": username.run,
    "phone": phone.run,
    "social": social.run,
    "address": address.run,
    "company": company.run,
    "domain": domain.run,
    "geoip": geoip.run,
    "certs": certs.run,
    "archive": archive.run,
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
