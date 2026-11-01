# What Fennec takes from the OSINT survey

The long survey lives in [osint-platforms.md](osint-platforms.md). Fennec only ships **local or low-traffic open-source** paths. No paid APIs, no login cookies, no port scans.

## Sidebar groups

| Group | Tools | Survey analogue |
|-------|--------|-----------------|
| **Basic** | Email, Name, Username, Phone | holehe; person name as a case fact; small public-profile URLs instead of full Maigret/Sherlock; phonenumbers / PhoneInfoga *local* fields (country, carrier, line type, timezone) |
| **Social** | Social profiles | A six-site existence check (Reddit, YouTube, Twitch, Pinterest, GitHub, TikTok). Not Instaloader, Osintgram, Toutatis, or GHunt |
| **Addresses** | Address, Company | Case fact for a postal line; Wikidata (one search + one entity) instead of OpenCorporates API |
| **Network** | Domain, IP network, Certificates, Web archive | dnspython + whoisdomain (RDAP); NetWatch-style local ASN/scope; **one** crt.sh query (capped names); **one** Wayback availability check. Not Amass, Subfinder, dnstwist, or gau dumps |
| **Files** | File metadata | Pillow EXIF/hash. ExifTool remains optional later |

## Explicitly out (for now)

- Full Maigret / Sherlock / WhatsMyName sweeps
- Breach APIs (HIBP, DeHashed, h8mail)
- Google cookies (GHunt), Instagram session tools, Telegram API
- Active recon: nmap, Nuclei, subdomain brute force
- Face search (PimEyes, FaceCheck)
- Dark-web crawlers (need Tor)
- Shodan/Censys keys (uncover `shodan-idb` could come later as a single IP lookup)

## Legal line (from the survey)

Lawful use only. Pakistan PECA 2016 ss.3, 16, 24 and similar computer-misuse rules elsewhere apply. Fennec stores results on this machine and does not phone home.
