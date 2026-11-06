from app.modules.base import ModuleResult, ModuleSpec
from app.modules import (
    address,
    archive,
    bgp,
    bitcoin,
    certs,
    chess,
    company,
    devto,
    dockerhub,
    domain,
    email,
    ethereum,
    geoip,
    geocode,
    github,
    gitlab,
    gravatar,
    greynoise,
    hackernews,
    internetdb,
    keybase,
    lichess,
    linkedin,
    metadata,
    name,
    npm,
    otx,
    person,
    pgp,
    phone,
    rdns,
    reddit,
    sanctions,
    securitytxt,
    social,
    stackoverflow,
    twitter,
    username,
    wikipedia,
)

DEFAULT_MODULES = [
    "email",
    "name",
    "person",
    "username",
    "phone",
    "wikipedia",
    "github",
    "gravatar",
    "pgp",
    "geoip",
]

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
        wikipedia.SPEC,
        github.SPEC,
        gitlab.SPEC,
        keybase.SPEC,
        npm.SPEC,
        dockerhub.SPEC,
        hackernews.SPEC,
        reddit.SPEC,
        chess.SPEC,
        lichess.SPEC,
        stackoverflow.SPEC,
        devto.SPEC,
        twitter.SPEC,
        linkedin.SPEC,
        gravatar.SPEC,
        pgp.SPEC,
        address.SPEC,
        company.SPEC,
        sanctions.SPEC,
        geocode.SPEC,
        domain.SPEC,
        geoip.SPEC,
        rdns.SPEC,
        internetdb.SPEC,
        bgp.SPEC,
        greynoise.SPEC,
        otx.SPEC,
        certs.SPEC,
        securitytxt.SPEC,
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
