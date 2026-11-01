# What Fennec takes from the OSINT survey

The long survey lives in [osint-platforms.md](osint-platforms.md). Fennec only ships **local or low-traffic open-source** paths. No paid APIs, no login cookies, no port scans.

## Sidebar groups

| Group | Tools | Survey analogue |
|-------|--------|-----------------|
| **Basic** | Email, Name, Username, Phone | holehe; person name as a case fact; small public-profile URLs instead of full Maigret/Sherlock; phonenumbers / PhoneInfoga *local* fields (country, carrier, line type, timezone) |
| **Social** | Social profiles, GitHub | Six-site existence check plus one GitHub API user lookup (OctoSuite-lite). Not Instaloader, Osintgram, Toutatis, or GHunt |
| **Addresses** | Address, Company | Case fact for a postal line; Wikidata (one search + one entity) instead of OpenCorporates API |
| **Network** | Domain, IP network, Reverse DNS, InternetDB, Certificates, Web archive | dnspython + whoisdomain; local ASN/scope; one PTR; one keyless Shodan InternetDB call; one crt.sh query; one Wayback check. Not Amass, Subfinder, dnstwist, or gau dumps |
| **Crypto** | Bitcoin | One mempool.space address lookup |
| **Files** | File metadata | Pillow EXIF/hash. ExifTool remains optional later |

## Explicitly out (for now)

- Full Maigret / Sherlock / WhatsMyName sweeps
- Breach APIs (HIBP, DeHashed, h8mail)
- Google cookies (GHunt), Instagram session tools, Telegram API
- Active recon: nmap, Nuclei, subdomain brute force
- Face search (PimEyes, FaceCheck)
- Dark-web crawlers (need Tor)
- Shodan/Censys paid keys (InternetDB is the keyless single-IP path)

## Legal line (from the survey)

Lawful use only. Pakistan PECA 2016 ss.3, 16, 24 and similar computer-misuse rules elsewhere apply. Fennec stores results on this machine and does not phone home.
