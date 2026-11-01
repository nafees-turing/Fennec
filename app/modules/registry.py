from app.modules.base import ModuleResult, ModuleSpec
from app.modules import (
    address,
    archive,
    bgp,
    bitcoin,
    certs,
    company,
    domain,
    email,
    ethereum,
    geoip,
    github,
    gravatar,
    internetdb,
    metadata,
    name,
    person,
    phone,
    rdns,
    sanctions,
    social,
    username,
)

CATEGORIES = [
    ("basic", "Basic"),
    ("social", "Social"),
    ("addresses", "Addresses"),
    ("network", "Network"),
    ("crypto", "Crypto"),
    ("files", "Files"),
]

_SPECS = {
    item.id: item
    for item in [
        email.SPEC,
        name.SPEC,
        person.SPEC,
        username.SPEC,
        phone.SPEC,
        social.SPEC,
        github.SPEC,
        gravatar.SPEC,
        address.SPEC,
        company.SPEC,
        sanctions.SPEC,
        domain.SPEC,
        geoip.SPEC,
        rdns.SPEC,
        internetdb.SPEC,
        bgp.SPEC,
        certs.SPEC,
        archive.SPEC,
        bitcoin.SPEC,
        ethereum.SPEC,
        metadata.SPEC,
    ]
}
_RUNNERS = {
    spec.id: __import__(f"app.modules.{spec.id}", fromlist=["run"]).run
    for spec in _SPECS.values()
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
