import ipaddress
import re
from urllib.parse import urlparse

from app.modules.bitcoin import BTC
from app.modules.domain import HOST, normalize_host
from app.modules.ethereum import ETH

EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
USER = re.compile(r"^[A-Za-z0-9._-]{2,39}$")
PHONE_COMPACT = re.compile(r"^\+[1-9]\d{7,14}$")
COMPANY_HINT = re.compile(
    r"\b(ltd|llc|inc|corp|gmbh|plc|oy|ab|sarl|bv|pty|limited|incorporated|company)\b",
    re.I,
)
STREET_HINT = re.compile(
    r"\b(street|st\.|road|rd\.|avenue|ave\.|lane|ln\.|drive|dr\.|boulevard|blvd|suite|floor|po box)\b",
    re.I,
)


def _match(module: str, value: str, label: str, kind: str) -> dict:
    return {"module": module, "value": value, "label": label, "kind": kind}


def classify(raw: str) -> dict:
    text = re.sub(r"\s+", " ", raw).strip()
    if not text:
        return {"detected": None, "matches": []}

    compact = re.sub(r"[\s().-]", "", text)
    if compact.startswith("00") and compact[2:].isdigit():
        compact = "+" + compact[2:]
    elif compact.isdigit() and len(compact) >= 10:
        compact = "+" + compact

    if EMAIL.fullmatch(text.lower()):
        email = text.lower()
        host = email.split("@", 1)[1]
        matches = [
            _match("email", email, "Email", "email"),
            _match("domain", host, "Mailbox domain", "domain"),
            _match("gravatar", email, "Gravatar", "email"),
            _match("pgp", email, "PGP", "email"),
        ]
        return {"detected": "email", "matches": matches}

    if PHONE_COMPACT.fullmatch(compact):
        return {
            "detected": "phone",
            "matches": [_match("phone", compact, "Phone", "phone")],
        }

    try:
        ipaddress.ip_address(text)
        return {
            "detected": "ip",
            "matches": [
                _match("geoip", text, "IP network", "ip"),
                _match("rdns", text, "Reverse DNS", "ip"),
                _match("internetdb", text, "InternetDB", "ip"),
                _match("bgp", text, "BGP", "ip"),
                _match("greynoise", text, "GreyNoise", "ip"),
                _match("otx", text, "OTX", "ip"),
            ],
        }
    except ValueError:
        pass

    host = ""
    if "://" in text or text.startswith("www."):
        parsed = urlparse(text if "://" in text else "https://" + text)
        host = (parsed.hostname or "").lower().lstrip("www.")
    elif HOST.fullmatch(text.lower().strip(".")):
        host = normalize_host(text)

    if host and HOST.fullmatch(host):
        return {
            "detected": "domain",
            "matches": [
                _match("domain", host, "Domain", "domain"),
                _match("certs", host, "Certificates", "domain"),
                _match("archive", host, "Web archive", "domain"),
                _match("securitytxt", host, "security.txt", "domain"),
            ],
        }

    if COMPANY_HINT.search(text):
        return {
            "detected": "company",
            "matches": [
                _match("company", text, "Company", "company"),
                _match("sanctions", text, "Sanctions", "company"),
            ],
        }

    if "," in text or STREET_HINT.search(text):
        return {
            "detected": "address",
            "matches": [
                _match("address", text, "Address", "address"),
                _match("geocode", text, "Geocode", "address"),
            ],
        }

    if " " in text:
        return {
            "detected": "name",
            "matches": [
                _match("name", text, "Person name", "name"),
                _match("person", text, "Wikidata person", "name"),
                _match("sanctions", text, "Sanctions", "name"),
                _match("wikipedia", text, "Wikipedia", "name"),
                _match("stackoverflow", text, "Stack Overflow", "name"),
            ],
        }

    handle = text[1:] if text.startswith("@") else text
    if USER.fullmatch(handle):
        return {
            "detected": "username",
            "matches": [
                _match("username", handle, "Username", "username"),
                _match("social", handle, "Social profiles", "username"),
                _match("github", handle, "GitHub", "username"),
                _match("gitlab", handle, "GitLab", "username"),
                _match("keybase", handle, "Keybase", "username"),
                _match("npm", handle, "npm", "username"),
                _match("dockerhub", handle, "Docker Hub", "username"),
                _match("hackernews", handle, "Hacker News", "username"),
                _match("reddit", handle, "Reddit", "username"),
                _match("chess", handle, "Chess.com", "username"),
                _match("lichess", handle, "Lichess", "username"),
                _match("stackoverflow", handle, "Stack Overflow", "username"),
                _match("devto", handle, "DEV", "username"),
            ],
        }

    if BTC.fullmatch(text):
        return {
            "detected": "bitcoin",
            "matches": [_match("bitcoin", text, "Bitcoin", "wallet")],
        }

    if ETH.fullmatch(text):
        return {
            "detected": "ethereum",
            "matches": [_match("ethereum", text, "Ethereum", "wallet")],
        }

    return {"detected": None, "matches": []}
