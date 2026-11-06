# What Fennec takes from the OSINT survey

The long survey lives in [osint-platforms.md](osint-platforms.md). Fennec only ships **local or low-traffic open-source** paths. No paid APIs, no login cookies, no port scans.

## Sidebar groups

| Group | Tools | Survey analogue |
|-------|--------|-----------------|
| **Basic** | Email, Name, Person, Wikipedia, Username, Phone, PGP | holehe; local name; Wikidata; Wikipedia summary; phonenumbers; keys.openpgp.org |
| **Social** | … plus X/Twitter and LinkedIn as **public URL checks only** (403 is not a hit; no login scrape) | One-call **person** profile APIs |
| **Addresses** | Address, Company, Sanctions, Geocode | Postal line; Wikidata org; OpenSanctions; one Nominatim search |
| **Network** | Domain, IP, Reverse DNS, InternetDB, BGP, GreyNoise, OTX, Certificates, security.txt, Web archive | DNS/RDAP; PTR; InternetDB; BGPView; GreyNoise; AlienVault OTX; crt.sh; RFC 9116; Wayback |
| **Crypto** | Bitcoin, Ethereum | mempool.space; Blockscout |
| **Files** | File metadata | Pillow EXIF/hash. ExifTool remains optional later |

## Explicitly out (for now)

- Full Maigret / Sherlock / WhatsMyName sweeps
- Breach APIs (HIBP, DeHashed, h8mail)
- Google cookies (GHunt), Instagram session tools, Telegram API
- Active recon: nmap, Nuclei, subdomain brute force
- Face search (PimEyes, FaceCheck)
- Dark-web crawlers (need Tor)
- Shodan/Censys paid keys (InternetDB is the keyless single-IP path)
- Vessels, aircraft, AIS, ADS-B, OpenSky, MarineTraffic, tail numbers, ICAO24, MMSI. Out of scope. Fennec is for **people and the accounts, emails, phones, and hosts around them**.

## Legal line (from the survey)

Lawful use only. Pakistan PECA 2016 ss.3, 16, 24 and similar computer-misuse rules elsewhere apply. Fennec stores results on this machine and does not phone home.
