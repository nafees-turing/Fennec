from app.modules.base import ModuleResult, ModuleSpec
from app.modules import phone

PLANNED = [
    ModuleSpec(
        id="username",
        title="Username",
        milestone="M2",
        summary="Profile search through Maigret.",
        input_label="Username",
        placeholder="someone",
        available=False,
        reason="Adapter is registered. Maigret runs in M2.",
    ),
    ModuleSpec(
        id="email",
        title="Email",
        milestone="M3",
        summary="Sites where an email is registered, through Holehe.",
        input_label="Email",
        placeholder="name@example.com",
        available=False,
        reason="Adapter is registered. Holehe runs in M3.",
    ),
    ModuleSpec(
        id="domain",
        title="Domain",
        milestone="M4",
        summary="DNS plus RDAP/WHOIS through whoisdomain.",
        input_label="Domain",
        placeholder="example.com",
        available=False,
        reason="Adapter is registered. DNS and WHOIS run in M4.",
    ),
    ModuleSpec(
        id="metadata",
        title="File metadata",
        milestone="M6",
        summary="EXIF and document metadata through ExifTool.",
        input_label="Not available yet",
        placeholder="",
        available=False,
        reason="File upload arrives with the ExifTool adapter in M6.",
    ),
]

_SPECS = {item.id: item for item in [phone.SPEC, *PLANNED]}
_RUNNERS = {"phone": phone.run}


def list_modules() -> list[ModuleSpec]:
    return list(_SPECS.values())


def get_module(module_id: str) -> ModuleSpec | None:
    return _SPECS.get(module_id)


def execute(module_id: str, value: str) -> ModuleResult:
    spec = _SPECS[module_id]
    if not spec.available:
        raise RuntimeError(spec.reason)
    return _RUNNERS[module_id](value)
