from app.modules.base import ModuleResult, ModuleSpec
from app.modules import domain, email, metadata, phone

PLANNED = [
    ModuleSpec(
        id="username",
        title="Username",
        milestone="M2",
        summary="Maigret hits a large number of sites. It stays off until we can run a small, slow set.",
        input_label="Username",
        placeholder="someone",
        available=False,
        reason="Skipped for now: a full username sweep is too many outbound requests.",
        network=True,
    ),
]

_SPECS = {item.id: item for item in [email.SPEC, phone.SPEC, domain.SPEC, metadata.SPEC, *PLANNED]}
_RUNNERS = {
    "email": email.run,
    "phone": phone.run,
    "domain": domain.run,
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
