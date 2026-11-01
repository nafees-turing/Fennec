# What Fennec takes from the OSINT survey

The long survey lives in [osint-platforms.md](osint-platforms.md). Fennec only ships **local or low-traffic open-source** paths. No paid APIs, no login cookies, no port scans.

## Sidebar groups

| Group | Tools | Survey analogue |
|-------|--------|-----------------|
| **Basic** | Email, Name, Person, Username, Phone | holehe; local name fact; Wikidata person (one search + one fetch); small profile URLs; phonenumbers local fields |
| **Social** | Social profiles, GitHub, Gravatar | Six-site existence check; one GitHub user call; one Gravatar JSON call |
| **Addresses** | Address, Company, Sanctions | Postal line; Wikidata org; one OpenSanctions search |
| **Network** | Domain, IP, Reverse DNS, InternetDB, BGP, Certificates, Web archive | DNS/RDAP; local ASN; PTR; InternetDB; BGPView; crt.sh; Wayback |
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

## Legal line (from the survey)

Lawful use only. Pakistan PECA 2016 ss.3, 16, 24 and similar computer-misuse rules elsewhere apply. Fennec stores results on this machine and does not phone home.
