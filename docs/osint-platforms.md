# OSINT Platforms & Tools: What They Are, What They Find, and Where They Get It

**Prepared for:** Nafees Ahmad
**Date:** November 2, 2026 (revision 2, after review round 1)
**Method:** Every tool below was checked against its official site or GitHub repo on Nov 1–2, 2026. Star counts and licences come from the GitHub REST API (`https://api.github.com/repos/<owner>/<repo>`); each star count links to that API record. **"Last commit"** is the newest commit on the repo's **default branch** (from `github.com/<repo>/commits.atom`). **"Last push"** is GitHub's `pushed_at`, which also counts pushes to *any* other branch. Both are shown where they differ. Capabilities come from each project's README or official docs. Prices are copied from vendor pricing pages on the check date and may change.

### Status legend (used everywhere in this report)

| Mark | Meaning (measured by **last default-branch commit**, as of Nov 2, 2026) |
|---|---|
| ✅ | Active: last commit **less than 3 months** ago (after Aug 2, 2026) |
| 🟡 | Slowing: last commit **3–12 months** ago |
| ❌ | Stale: last commit **more than 12 months** ago, **or** archived / repurposed |

Footnote ¹: if every recent commit is trivial (sponsor links, README or badge edits only), the date of the **last code change** is used instead. This currently applies only to **Photon**.

---

## TL;DR

- **Best free all-round framework: SpiderFoot** (MIT, [24,208★](https://api.github.com/repos/smicallef/spiderfoot), [233 `sfp_*` modules](https://github.com/smicallef/spiderfoot/tree/master/modules), 10 input types). Its default branch hasn't had a commit since **2023-11-05**, so it is ❌ by the legend. It still works but is frozen. Intel 471 bought the company in 2022, and `spiderfoot.net` now redirects to intel471.com.
- **Usernames:** **Sherlock** ([95,371★](https://api.github.com/repos/sherlock-project/sherlock), [481 site entries](https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json)) for speed. **Maigret** ([39,602★](https://api.github.com/repos/soxoj/maigret), 5,900 sites per its README, extracts profile data, searches recursively) for depth. **WhatsMyName** ([692 sites](https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json), CC BY-SA 4.0) is the dataset many other tools are built on.
- **Email → accounts:** **holehe** (120+ sites; ❌, last commit Sep 2024). **GHunt** (Google accounts; 🟡, last commit Apr 2026). **Blackbird** (600+ platforms, ✅). ⚠️ **Blackbird has no licence file**, so it is source-available, not open source.
- **Instagram:** **Instaloader** (MIT, ✅) downloads public profiles without a login. **Toutatis** needs a session cookie and returns obfuscated email and phone.
- **Domains and infrastructure:** **OWASP Amass**, **Subfinder**, and **theHarvester** are all ✅. **uncover** queries **19 engines** at once, and its keyless `shodan-idb` engine works with no API key. **dnstwist** finds lookalike and phishing domains. **gau** pulls historical URLs.
- **Threat intel on IPs, hashes, and domains:** **IntelOwl** (AGPL-3.0, ✅).
- **Stale or risky:** Twint (archived), OSRFramework (repo repurposed), snscrape, h8mail, holehe, Sublist3r, and Photon¹ are all ❌. **PhoneInfoga** is ✅ by commit date, but its author calls it "stable but unmaintained".
- **Commercial leaders:** Maltego, Shodan, Censys, Intelligence X, DeHashed, HIBP, OSINT Industries, Epieos, PimEyes, and FaceCheck, plus enterprise suites. Section 3 has details and price links.
- **Legal:** In Pakistan, **PECA 2016** criminalises unauthorised access (s.3), misuse of identity information (s.16), and **cyberstalking (s.24)**. The **Personal Data Protection Bill is still a draft**. See Section 6.

### Starter kits: one install line each (all free and open source)

| Goal | Install | First command | Key or login? |
|---|---|---|---|
| **Username → accounts** | `pip3 install maigret` ([README](https://github.com/soxoj/maigret)) · `pipx install sherlock-project` ([README](https://github.com/sherlock-project/sherlock)) | `maigret <user>` · `sherlock <user>` | None |
| **Email → accounts** | `pip3 install holehe` ([README](https://github.com/megadose/holehe)) · `pipx install ghunt` ([README](https://github.com/mxrch/GHunt)) | `holehe <email>` · `ghunt login` then `ghunt email <email>` | holehe: none. GHunt: Google cookies |
| **Domain → attack surface** | `go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest` ([README](https://github.com/projectdiscovery/subfinder)) · `pip install dnstwist[full]` ([README](https://github.com/elceef/dnstwist)) · `go install github.com/lc/gau/v2/cmd/gau@latest` ([README](https://github.com/lc/gau)) | `subfinder -d example.com` · `dnstwist --registered example.com` · `gau example.com` | None to start (optional source keys) |
| **Phone → messaging accounts** | `pip3 install ignorant` ([README](https://github.com/megadose/ignorant)) · Bellingcat [TG checker](https://github.com/bellingcat/telegram-phone-number-checker) | `ignorant 33 644637111` (country code, number) | ignorant: none. TG checker: Telegram API ID and hash |
| **Image → origin / location** | `sudo apt install libimage-exiftool-perl` ([Kali/Debian package](https://www.kali.org/tools/libimage-exiftool-perl/)) | `exiftool -a -G1 photo.jpg`, then reverse-search the image on [Google Lens](https://search.google/ways-to-search/lens/), [Bing](https://www.bing.com/images) (camera icon), [Yandex](https://yandex.com/images/), [TinEye](https://tineye.com/) | None |

---

## 1. What OSINT is and what open sources exist

**Open-Source Intelligence (OSINT)** means collecting and analysing information from publicly available sources to answer an intelligence question. Security teams, journalists, fraud and KYC teams, law enforcement, and red teams all use it. "Open source" here means the **data** is public. It doesn't mean the **software** is open source. This report covers both.

### Main categories of open-source data

| Category | Typical selectors (inputs) | What can be learned | Typical sources |
|---|---|---|---|
| **People / identity** | Full name, DOB, address | Public records, associations, photos, employers | People-search sites, court and company registries, news, social media |
| **Usernames / social media** | Handle, profile URL | Which platforms the handle is on, bios, linked accounts, posts, followers, geotags, posting times | Hundreds of social sites, forums, dating sites, and gaming platforms |
| **Email** | Email address | Registered accounts (via sign-up and password-reset checks), Google account data, breach exposure, linked phone or recovery hints | Site password-reset flows, Google services, breach DBs, Gravatar, PGP keyservers |
| **Phone** | E.164 number | Country, carrier, line type, messaging-app accounts (Telegram, WhatsApp, Signal), caller-ID names, spam reports | Numbering plans, messaging APIs, caller-ID databases, search engines |
| **Domains / DNS / WHOIS / certificates** | Domain | Subdomains, DNS records, registrant (often redacted after GDPR), historical WHOIS and DNS, TLS certificates, lookalike domains, archived URLs | Certificate Transparency logs (crt.sh, CertSpotter), passive DNS, WHOIS/RDAP, Wayback Machine |
| **IP / infrastructure / internet scanning** | IP, CIDR, ASN | Open ports, banners, software versions, CVEs, TLS certs, hosting provider and ASN, geolocation, scanner "noise" classification | Shodan, Censys, FOFA, ZoomEye, Netlas, GreyNoise, BGP and RIR registries |
| **Breach / leak data** | Email, username, domain, password hash | Which breaches an identifier appears in, exposed data classes, sometimes cleartext passwords or hashes, stealer-log hits | HIBP, DeHashed, Intelligence X, Snusbase, Leak-Lookup |
| **Images / geolocation / metadata** | Photo, video, document | EXIF GPS, camera model, author, timestamps, reverse-image matches, face matches, sun and shadow position | ExifTool, Google Lens, Bing, Yandex, TinEye, PimEyes, FaceCheck, SunCalc |
| **Maritime / aviation tracking** | Vessel name, IMO/MMSI, tail number, ICAO24 hex | Live and historical position, routes, port calls, encounters, ownership | AIS (MarineTraffic, VesselFinder, Global Fishing Watch); ADS-B and MLAT (ADS-B Exchange, OpenSky, Flightradar24) |
| **Corporate / financial records** | Company name or number, LEI | Officers, shareholders, filings, addresses, sanctions and PEP status | OpenCorporates, UK Companies House, SEC EDGAR, GLEIF, OpenSanctions |
| **Crypto** | BTC/ETH address, transaction hash | Balances, transaction graph, labelled entities | Block explorers (mempool.space, Etherscan), SpiderFoot extraction, IntelX |
| **Dark web** | Keyword, email, domain, crypto address | Mentions on .onion and .i2p sites, leak sites, markets, pastes | Ahmia, OnionSearch, Intelligence X (Tor/I2P buckets), commercial CTI |
| **Code repositories** | Org, username, domain, keyword | Leaked secrets, internal hostnames, employee emails in commits | GitHub, GitLab, OctoSuite |
| **Web archives** | URL, domain | Deleted pages, old contact info, historical site content and URLs | Wayback Machine, Common Crawl, gau/waybackurls, Bellingcat auto-archiver |

---

## 2. Open-source and free OSINT tools (verified Nov 2026)

Status marks follow the legend at the top. Dates are YYYY-MM-DD.

### 2.1 Automation frameworks (multi-input)

#### SpiderFoot (open-source edition)
- **Link:** https://github.com/smicallef/spiderfoot (primary). The old site `https://www.spiderfoot.net/` now **301-redirects to intel471.com**.
- **Licence / language:** MIT · Python 3
- **Stars / dates:** [24,208★](https://api.github.com/repos/smicallef/spiderfoot) · last commit **2023-11-05** · last push 2026-04-13 (another branch) · ❌ frozen
- **Key / login:** Most modules need no key. The README says that "many of those that do require API keys have a free tier".
- **Inputs:** IP address, domain or subdomain, hostname, CIDR subnet, ASN, email address, phone number, username, person's name, Bitcoin address.
- **What it collects:** The README says "over 200 modules", and the [`modules/` directory](https://github.com/smicallef/spiderfoot/tree/master/modules) holds **233 `sfp_*` files**. They run in a publish/subscribe chain:
  - Subdomain and host enumeration, DNS zone transfers, subdomain-takeover checks
  - Emails, phone numbers, and human names extracted from web content
  - Bitcoin and Ethereum addresses
  - Threat-intel and blacklist lookups (abuse.ch, AbuseIPDB, AlienVault OTX, GreyNoise, and others)
  - API integrations (Shodan, HaveIBeenPwned, SecurityTrails, BinaryEdge, and more)
  - Social-media account enumeration
  - S3, Azure, and DigitalOcean bucket enumeration
  - Geolocation, web scraping, and metadata analysis
  - Dark-web searches (Ahmia, Tor)
  - Port scanning, breach searches, Wayback history
- **Extras:** Web UI and CLI, a YAML correlation engine, export to CSV/JSON/GEXF, a SQLite backend.
- **Limits:** No fixes since 2023, so some third-party modules break as APIs change. Intel 471 [acquired SpiderFoot](https://www.intel471.com/company/press-releases/intel-471-acquires-spiderfoot) in 2022.

#### Recon-ng
- **Link:** https://github.com/lanmaster53/recon-ng · modules: https://github.com/lanmaster53/recon-ng-marketplace
- **Licence / language:** GPL-3.0 · Python
- **Stars / dates:** [6,023★](https://api.github.com/repos/lanmaster53/recon-ng) · last commit 2026-10-05 ✅
- **Key / login:** Many modules need API keys (some free).
- **Inputs:** Workspaces seeded with domains, companies, netblocks, contacts, profiles, or locations.
- **What it collects:** A Metasploit-style modular framework. [`modules.yml`](https://raw.githubusercontent.com/lanmaster53/recon-ng-marketplace/master/modules.yml) lists **109 modules**. The largest groups are `domains-hosts` (16), `hosts-hosts` (10), `domains-contacts` (6), and `companies-multi` (5). There are also `profiles-profiles`, `netblocks-hosts`, `locations-pushpins` (geotagged media), `contacts-credentials`, and `repositories-vulnerabilities`. Output is a relational DB of hosts, contacts, credentials, profiles, locations, and vulnerabilities.

#### theHarvester
- **Link:** https://github.com/laramies/theHarvester
- **Licence / language:** GPL-2.0 · Python (uses `uv`)
- **Stars / dates:** [18,208★](https://api.github.com/repos/laramies/theHarvester) · last commit 2026-10-20 · last push 2026-10-30 ✅
- **Key / login:** Keyless sources work (e.g. `-b crtsh,certspotter`). Some sources need keys.
- **Inputs:** Domain or organisation.
- **What it collects:** Subdomains, emails, IPs, ASNs, and URLs. Sources include search engines, CT logs, DNS datasets, Common Crawl, code repositories, and threat-intel platforms. It also has a local HarvestView web UI, a REST API, and a SQLite evidence store.
- **Activity classes:** **P0** is passive (third party only). **P1** is DNS queries and brute force. **P2** makes direct contact (HTTP/TLS, screenshots, ports). P1 and P2 run only when you enable them, and only against authorised targets.

#### IntelOwl
- **Link:** https://github.com/intelowlproject/IntelOwl · docs https://intelowlproject.github.io/docs/
- **Licence / language:** AGPL-3.0 · Python (Django)
- **Stars / dates:** [4,780★](https://api.github.com/repos/intelowlproject/IntelOwl) · last commit 2026-09-02 (default branch `master`) · last push 2026-10-31 ✅
- **Key / login:** Each external analyzer has its own key (e.g. VirusTotal, AbuseIPDB). Local analyzers such as YARA need none.
- **Inputs / output:** Observables (IP, domain, URL, hash) and files. Returns threat-intel enrichment and file analysis, with playbooks, pivots, MISP and OpenCTI export, a GUI, and a REST API.

#### DataSploit
- **Link:** https://github.com/DataSploit/datasploit · GPL-3.0 · Python
- **Stars / dates:** [3,332★](https://api.github.com/repos/DataSploit/datasploit) · last commit 2025-11-20 (added Python 3 support after years of inactivity) 🟡
- **Key / login:** API keys go in a config file.
- **Inputs / output:** Domain, email, IP, or username. Finds credentials, API keys, tokens, subdomains, domain history, and legacy portals. Reports are HTML, JSON, or text.

#### FinalRecon
- **Link:** https://github.com/thewhiteh4t/FinalRecon · MIT · Python
- **Stars / dates:** [3,042★](https://api.github.com/repos/thewhiteh4t/FinalRecon) · last commit 2026-10-31 ✅
- **Key / login:** API keys are optional, and modules without a key are skipped.
- **Inputs / output:** URL or domain. Returns:
  - HTTP headers (flags missing security headers)
  - WHOIS, SSL certificate, DNS
  - Crawler output and subdomains
  - Wayback URLs
  - A top-1000 port scan (active)

#### reNgine
- **Link:** https://github.com/yogeshojha/rengine · GPL-3.0 · Python (Django web app, Docker)
- **Stars / dates:** [8,912★](https://api.github.com/repos/yogeshojha/rengine) · last commit 2025-11-16 (default branch `master`) · last push 2026-10-31 (another branch) 🟡
- **Key / login:** None to start. GPT report and attack-surface features use OpenAI's GPT, so they need an OpenAI key.
- **Input:** Domain(s).
- **What it finds (README):**
  - Subdomains, IPs and open ports, endpoints, and directory/file fuzzing results
  - Screenshots, WHOIS, WAF detection
  - Vulnerability scans with Nuclei, Dalfox (XSS), CRLFuzzer, and a misconfigured-S3 scanner
  - **OSINT on the target org:** meta info from public documents, **employee names**, **email addresses**, and Google dorks for sensitive files
  - Continuous monitoring, PDF reports, and GPT-written report sections; chaos was added as a subdomain source in v2.2.0
- Much of this is **active scanning** (see Section 6).

#### Osmedeus
- **Link:** https://github.com/j3ssie/osmedeus · site https://www.osmedeus.org/ · MIT · Go
- **Stars / dates:** [6,637★](https://api.github.com/repos/j3ssie/osmedeus) · last commit 2026-10-04 ✅
- **Key / login:** None for the engine itself. Wrapped tools may need their own keys.
- **Input:** Target domain, IP, or list (e.g. `osmedeus run -m recon -t example.com`).
- **What it does (README):**
  - A declarative YAML workflow engine that chains recon tools into pipelines, run as modules (e.g. `-m recon`). Modules can be skipped with `-x portscan`.
  - 80+ built-in utility functions, including **nmap integration** and **CDN/WAF classification**
  - Distributed workers and cloud scanning
  - A REST API and web UI with asset and vulnerability views, plus optional LLM ("agentic") steps
- **Install:** `npm install -g @j3ssie/osmedeus` or the install script on osmedeus.org.

### 2.2 Username and social-media tools

#### Sherlock
- **Link:** https://github.com/sherlock-project/sherlock · site https://sherlockproject.xyz/ · MIT · Python
- **Stars / dates:** [95,371★](https://api.github.com/repos/sherlock-project/sherlock) · last commit 2026-11-01 ✅
- **Key / login:** None. Install with `pipx install sherlock-project`.
- **What it finds:** Whether a username exists on "400+ social networks". Its live [`data.json`](https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json) had **481** site entries on Nov 2, 2026. Outputs profile URLs (txt, csv, xlsx, json) and supports Tor and proxies.
- **Limits:** Checks existence only, with no profile data. Some results are false positives.

#### Maigret
- **Link:** https://github.com/soxoj/maigret · docs https://maigret.readthedocs.io/ · MIT · Python
- **Stars / dates:** [39,602★](https://api.github.com/repos/soxoj/maigret) · last commit 2026-10-29 · last push 2026-10-31 ✅
- **Key / login:** "No API keys required" (README).
- **What it finds:**
  - Accounts on **5,900 sites** (README). By default it checks the top 500; `-a` checks all.
  - **Profile data** extracted via `socid_extractor`: names, bios, links, other IDs
  - **Recursive search** on newly found usernames and IDs
  - Tor and I2P sites
  - HTML, PDF, and graph reports, a web UI, and optional AI summaries

#### WhatsMyName (WMN)
- **Link:** https://github.com/WebBreacher/WhatsMyName · web app https://whatsmyname.app/
- **Licence:** Data is **CC BY-SA 4.0** (GitHub reports it as "Other")
- **Stars / dates:** [3,004★](https://api.github.com/repos/WebBreacher/WhatsMyName) · last commit 2026-10-30 ✅
- **What it is:** A community JSON dataset ([`wmn-data.json`](https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json), **692 sites** on Nov 2, 2026). It has shipped **data only** since May 2023. A site must be public, include the username in its profile URL, and leave the username unchanged, which keeps false positives low.

#### Blackbird
- **Link:** https://github.com/antoniaci/blackbird (the old URL `github.com/p1ngul1n0/blackbird` now redirects here)
- **Licence / language:** ⚠️ **No licence file**, so it is source-available, not OSS · Python
- **Stars / dates:** [9,518★](https://api.github.com/repos/antoniaci/blackbird) · last commit 2026-10-17 ✅
- **Key / login:** None for searches. An API key is needed only for the optional AI profiling.
- **What it finds:** Accounts for a username **or email** on "more than 600 platforms" using WhatsMyName data. Exports a PDF report.

#### Social-Analyzer
- **Link:** https://github.com/qeeqbox/social-analyzer · AGPL-3.0 · Node.js and Python
- **Stars / dates:** [24,419★](https://api.github.com/repos/qeeqbox/social-analyzer) · last commit 2026-01-12 🟡
- **Key / login:** None.
- **What it finds:** Profiles for a username or name string (it builds permutations) across "1000+" sites. Each match gets a 0–100 confidence score. It also extracts metadata, takes screenshots, and analyses name origin and similarity, with optional search-engine queries and graphs.

#### Instaloader (Instagram)
- **Link:** https://github.com/instaloader/instaloader · docs https://instaloader.github.io/ · MIT · Python
- **Stars / dates:** [13,755★](https://api.github.com/repos/instaloader/instaloader) · last commit 2026-11-01 ✅
- **Key / login:** None for public profiles. `--login` is needed for private profiles you follow, stories, feed, and saved posts.
- **What it downloads:** Public and private profiles, hashtags, stories, feeds, saved media, **comments, geotags, and captions** for each post. It also **detects profile-name changes**. Install with `pip3 install instaloader`.

#### Osintgram (Instagram)
- **Link:** https://github.com/Datalux/Osintgram · GPL-3.0 · Python
- **Stars / dates:** [15,352★](https://api.github.com/repos/Datalux/Osintgram) · last commit 2026-10-26 · last push 2026-10-30 ✅
- **Key / login:** **Paid HikerAPI** or an Instagram login via `instagrapi`. The tool shows the cost before each run.
- **What it finds:** Followers and following, captions, hashtags, a **map of geotagged locations**, a posting-time heatmap, public contact details, and account comparison. Has a local web UI and an optional local AI mode (Ollama).

#### Toutatis (Instagram)
- **Link:** https://github.com/megadose/toutatis · GPL-3.0 · Python
- **Stars / dates:** [4,398★](https://api.github.com/repos/megadose/toutatis) · last commit 2024-12-05 ❌
- **Key / login:** **Instagram `sessionid` cookie** (use a research account).
- **What it finds:** For an IG username or ID: full name, user ID, verified, business, and private flags, follower, following, and post counts, external URL, bio, public email and phone, and **obfuscated (partial) email and phone**, plus the profile picture. Install with `pip install toutatis`.

#### Twint (Twitter/X) and snscrape
- **Twint:** https://github.com/twintproject/twint. ❌ **Archived** (last commit 2021-03-02, last push 2023-02-23). It no longer works against X.
- **snscrape:** https://github.com/JustAnotherArchivist/snscrape. GPL-3.0, [5,467★](https://api.github.com/repos/JustAnotherArchivist/snscrape). Last commit 2023-06-22, last push 2023-11-15. ❌ **Stale.** It scraped Facebook, Instagram, Mastodon, Reddit (via Pushshift), Telegram channels, Twitter, VKontakte, and Weibo, but many of those scrapers have broken as the platforms changed. Treat it as historical.

#### Mr.Holmes
- **Link:** https://github.com/Lucksi/Mr.Holmes · GPL-3.0 · Python
- **Stars / dates:** [4,356★](https://api.github.com/repos/Lucksi/Mr.Holmes) · last commit 2026-02-21 🟡
- **Key / login:** A WhoisXMLAPI key for the WHOIS module. The optional local GUI and database ship with **default credentials Admin/Qwerty123**, so change them.
- **What it finds (README):**
  - Information on **usernames, phone numbers, and domains** from public internet sources
  - Domain **WHOIS** through the WhoisXMLAPI key
  - **Google-dork** searches, including video, sound, and image dorks with date or date-range filters
  - Proxy support for anonymity, and reports that can be sent to your phone via QR code
- The README warns it is "not 100% accurate".

#### OSRFramework (i3visio)
- **Link (historic):** `github.com/i3visio/osrframework` (text only). The GitHub API now redirects it to `i3visio/solana-mev-bot`, an unrelated crypto repo, and the web URL ends in a 404. Last PyPI release: https://pypi.org/project/osrframework/ (0.20.5, 2021-11-24). ❌ Don't install it from GitHub.

#### OctoSuite (GitHub OSINT, Bellingcat)
- **Link:** https://github.com/bellingcat/octosuite · MIT · Python
- **Stars / dates:** [1,894★](https://api.github.com/repos/bellingcat/octosuite) · last commit 2026-10-26 ✅
- **Key / login:** None.
- **What it finds:**
  - **Users:** profile, repos, subscriptions, starred repos, followers and following, orgs, gists, events
  - **Repos:** profile, forks, branches, tags, languages, stargazers, subscribers, commits, comments, issues, releases, deployments
  - **Orgs:** profile, repos, events, hooks, issues, members
  - **Search:** repos, users, commits, issues, topics, with JSON export and a TUI
- Install with `pip install octosuite`.

### 2.3 Email and phone tools

#### holehe
- **Link:** https://github.com/megadose/holehe · GPL-3.0 · Python
- **Stars / dates:** [15,487★](https://api.github.com/repos/megadose/holehe) · last commit 2024-09-10 ❌
- **Key / login:** None. Install with `pip3 install holehe`.
- **What it finds:** Whether an email is registered on **120+ sites**. It checks password-recovery and registration flows, which the README says do **not alert the target**. Some sites also return **partially obfuscated recovery emails or phones**. Its hosted successor is OSINT Industries.

#### GHunt
- **Link:** https://github.com/mxrch/GHunt · AGPL-3.0 (GitHub shows "Other") · Python 3.10+
- **Stars / dates:** [19,762★](https://api.github.com/repos/mxrch/GHunt) · last commit **2026-04-10** (a merge of a cover-photo fix; the previous substantive fix was 2026-03-14, "Auth + Maps fixed !") 🟡
- **Key / login:** **Google cookies**, captured with the GHunt Companion browser extension.
- **Inputs:** Email, Gaia ID, Drive file or folder ID, BSSID, and Digital Asset Links.
- **What it finds for an email:** Whether a Google account exists, the Gaia ID, account type, last profile edit, profile photo, **Google Maps reviews and photos**, Calendar data if public, Play Games data, and Chat data. Output can be JSON.

#### socialscan
- **Link:** https://github.com/iojw/socialscan · MPL-2.0 · Python
- **Stars / dates:** [1,867★](https://api.github.com/repos/iojw/socialscan) · last commit 2024-01-21 · last push 2026-10-28 (another branch) ❌
- **Key / login:** None.
- **What it finds:** Whether an email or username is **available, taken, or invalid**, using each platform's registration endpoint:
  - Username and email: Instagram, Twitter, GitHub, Tumblr, Last.fm
  - Username only: Snapchat, GitLab, Reddit, Yahoo
  - Email only: Pinterest, Firefox
- Install with `pip install socialscan`.

#### mosint
- **Link:** https://github.com/alpkeskin/mosint · MIT · Go
- **Stars / dates:** [6,071★](https://api.github.com/repos/alpkeskin/mosint) · last commit 2023-09-19 · last push 2024-02-02 ❌
- **Key / login:** A **config file is required**. Hunter, EmailRep, psbdmp, IntelX, BreachDirectory, and HIBP need keys.
- **What it finds:** Email verification, linked social accounts, breaches and password leaks, related emails and domains, Pastebin dumps, Google results, and DNS/IP lookups. Install with `go install -v github.com/alpkeskin/mosint/v3/cmd/mosint@latest`.

#### h8mail
- **Link:** https://github.com/khast3x/h8mail · BSD-3-Clause (GitHub shows "Other") · Python
- **Stars / dates:** [5,364★](https://api.github.com/repos/khast3x/h8mail) · last commit 2022-06-25 · last push 2023-08-15 ❌
- **Key / login:** Paid breach APIs (Snusbase, Leak-Lookup, DeHashed, Intelligence X), plus HIBP and Hunter keys.
- **What it finds:** Breach hits for an email. With paid APIs or **local breach compilations**, it also returns cleartext passwords, hashes, usernames, and IPs. Some listed APIs (e.g. scylla.so) are dead. See Section 6 on breach data.

#### PhoneInfoga
- **Link:** https://github.com/sundowndev/phoneinfoga · docs https://sundowndev.github.io/phoneinfoga/ · GPL-3.0 · Go
- **Stars / dates:** [18,350★](https://api.github.com/repos/sundowndev/phoneinfoga) · last commit 2026-08-25 ✅ by date. However, the README says it is **"stable but unmaintained… could be archived at any time"**, and recent commits are test-only.
- **Key / login:** None for the basic local scan. The README says its scanners "must be configured in order for the tool to be effective".
- **What it finds:** Validity, country, area, **carrier, and line type**. It also searches APIs, phone books, and search engines for reputation, social mentions, and disposable-number status. Web UI and REST API. Per its README, it does **no** real-time tracking or precise location.

#### Telegram phone-number checker (Bellingcat)
- **Link:** https://github.com/bellingcat/telegram-phone-number-checker · MIT · Python
- **Stars / dates:** [1,868★](https://api.github.com/repos/bellingcat/telegram-phone-number-checker) · last commit 2026-08-17 ✅
- **Key / login:** A **Telegram account plus API ID and hash**. Bellingcat advises using a fresh account.
- **What it finds:** Whether each phone number has a Telegram account, plus the **username, name, and user ID**.

#### ignorant
- **Link:** https://github.com/megadose/ignorant · GPL-3.0 · Python
- **Stars / dates:** [2,137★](https://api.github.com/repos/megadose/ignorant) · last commit 2023-12-29 · last push 2024-07-27 ❌
- **Key / login:** None.
- **What it finds:** Whether a phone number is used on sites such as **Snapchat, Instagram, and Amazon**. The README says it "does not alert the target phone number". Usage: `ignorant 33 644637111`.

### 2.4 Domain, DNS, URL, and infrastructure tools

#### OWASP Amass
- **Link:** https://github.com/owasp-amass/amass · project page https://owasp.org/projects/amass · Apache-2.0 (GitHub shows "Other") · Go
- **Stars / dates:** [15,449★](https://api.github.com/repos/owasp-amass/amass) · last commit 2026-10-25 ✅
- **Key / login:** Optional keys per data source.
- **What it finds:** Subdomains and the network map behind them, stored in a graph DB. Install with `CGO_ENABLED=0 go install -v github.com/owasp-amass/amass/v5/cmd/amass@latest` (resolves to v5.1.3, released 2026-10-25, per the [Go module proxy](https://proxy.golang.org/github.com/owasp-amass/amass/v5/@latest)) or `docker pull owaspamass/amass` ([official image](https://hub.docker.com/r/owaspamass/amass)); the old `v4/...@master` path and `caffix/amass` image are stale (Sep 2023). Sources:
  - **APIs:** 360PassiveDNS, BinaryEdge, BuiltWith, Chaos, CIRCL, DNSDB, FOFA, FullHunt, GitHub, GreyNoise, HackerTarget, and more
  - **Certificates:** Censys, CertSpotter, crt.sh
  - **DNS:** brute force, reverse sweeping, NSEC walking, zone transfers, permutations
  - **Routing:** BGPTools, IPinfo, RADb, Team Cymru
  - **Scraping:** Bing, DuckDuckGo, DNSDumpster, RapidDNS
  - **Archives:** Common Crawl, Wayback, Arquivo
  - **WHOIS:** SecurityTrails, WhoisXMLAPI, ONYPHE

#### Subfinder (ProjectDiscovery)
- **Link:** https://github.com/projectdiscovery/subfinder · MIT · Go
- **Stars / dates:** [14,696★](https://api.github.com/repos/projectdiscovery/subfinder) · last commit 2026-10-31 ✅
- **Key / login:** Works right after install, but the README notes that "many sources required API keys to work".
- **What it finds:** Subdomains from **passive sources only**, such as crt.sh, GitHub, AlienVault, and ZoomEye (`-ls` lists them all). Fast, with JSON output and stdin/stdout support.

#### uncover (ProjectDiscovery)
- **Link:** https://github.com/projectdiscovery/uncover · MIT · Go
- **Stars / dates:** [3,102★](https://api.github.com/repos/projectdiscovery/uncover) · last commit 2026-10-27 ✅
- **Key / login:** Each engine needs its own API key, **except `shodan-idb`** (Shodan InternetDB), which is keyless and is the default for IP/CIDR input.
- **What it finds:** Exposed hosts from a search query, across **19 engines**: Shodan, **shodan-idb**, Censys, FOFA, Hunter (Qianxin), Quake, ZoomEye, Netlas, CriminalIP, PublicWWW, HunterHow, Google, ONYPHE, Driftnet, DayDayMap, NerdyData, **ODIN, BinaryEdge, and GreyNoise**.

#### Shodan CLI / Python library
- **Link:** https://github.com/achillean/shodan-python · install docs https://help.shodan.io/command-line-interface/0-installation
- **Licence / language:** **MIT** · Python
- **Stars / dates:** [3,461★](https://api.github.com/repos/achillean/shodan-python) · last commit 2023-12-17 · last push 2024-08-05 ❌ by the legend, but it is the official and stable client.
- **Key / login:** A **Shodan API key** (free account, limited; see Section 3).
- **What it does:** Shodan search, bulk IP lookups, the streaming firehose, network alerts, exploit search, and DNS lookups.

#### dnstwist
- **Link:** https://github.com/elceef/dnstwist · web version https://dnstwist.it/ · Apache-2.0 · Python
- **Stars / dates:** [5,769★](https://api.github.com/repos/elceef/dnstwist) · last commit 2025-04-15 ❌ (mature tool)
- **Key / login:** None. Install with `pip install dnstwist[full]`.
- **What it finds:** **Lookalike domains** for typosquatting, phishing, and brand-impersonation checks. It generates permutations, including Unicode (IDN) ones and dictionary-based variants, then checks which are in use. Its detections:
  - **Live phishing pages**, via HTML fuzzy hashes (ssdeep/tlsh) and screenshot pHash similarity
  - **Rogue MX hosts** that intercept misdirected email
  - GeoIP location
- Outputs CSV or JSON.

#### gau and waybackurls (historical URLs)
- **gau:** https://github.com/lc/gau. MIT, Go, [5,152★](https://api.github.com/repos/lc/gau), last commit 2026-10-12 ✅. Fetches **known URLs for a domain** from AlienVault OTX, the **Wayback Machine, Common Crawl, and URLScan**. Install with `go install github.com/lc/gau/v2/cmd/gau@latest`. Needs no key.
- **waybackurls:** https://github.com/tomnomnom/waybackurls. **No licence file**, Go, [4,598★](https://api.github.com/repos/tomnomnom/waybackurls). Last commit 2022-04-05, last push 2024-05-01 ❌. Lists every Wayback Machine URL for `*.domain`. Install with `go install github.com/tomnomnom/waybackurls@latest`.
- **Why they matter:** Old URLs expose deleted pages, forgotten endpoints, parameters, and documents.

#### Sublist3r
- https://github.com/aboul3la/Sublist3r. GPL-2.0, last commit 2020-07-29, last push 2024-08-02 ❌. A classic subdomain enumerator, now superseded by Subfinder and Amass.

#### sn0int
- **Link:** https://github.com/kpcyrd/sn0int · registry https://sn0int.com/ · GPL-3.0 · Rust
- **Stars / dates:** [2,559★](https://api.github.com/repos/kpcyrd/sn0int) · last commit 2026-09-20 ✅
- **Key / login:** None for the core framework.
- **What it does:** A semi-automatic OSINT framework and package manager. Its modules run sandboxed. The README lists:
  - Subdomains from CT logs and passive DNS, mass DNS resolution, and http/https probing
  - ASN and GeoIP enrichment of IPs
  - **Emails from PGP keyservers and WHOIS**
  - **Compromised logins in breaches**
  - **Profiles across the internet** and social-media activity and images
  - Phone-number info, passive ARP, and basic image processing

### 2.5 Web crawling, documents, metadata, dark web, and archiving

#### Photon
- **Link:** https://github.com/s0md3v/Photon · GPL-3.0 · Python
- **Stars / dates:** [13,317★](https://api.github.com/repos/s0md3v/Photon) · last commit 2026-10-17, but [every commit since 2019-12-06](https://github.com/s0md3v/Photon/commits/master) only touches sponsor or README text. **Last code change: 2019-12-06** → ❌¹
- **Key / login:** None.
- **What it extracts:** In-scope and external URLs, URLs with parameters, **emails, social accounts, Amazon buckets**, files, **secret keys and hashes**, JS files and endpoints, regex matches, and subdomains. It can seed its crawl from Wayback URLs.

#### Metagoofil
- **Maintained fork:** https://github.com/opsdisk/metagoofil. **GPL-3.0** ([603★](https://api.github.com/repos/opsdisk/metagoofil)), last commit 2026-10-31 ✅. This is the version Kali packages.
- **Original:** https://github.com/laramies/metagoofil. **GPL-2.0**, last commit 2015-08-13, last push 2024-03-21 ❌.
- **What it does:** Uses Google dorks (`site:example.com filetype:pdf`) to **find and download public documents**. Pass them to ExifTool for metadata such as author, creator, producer, and software. Google may rate-limit it (HTTP 429).

#### ExifTool
- **Link:** https://exiftool.org/ · mirror https://github.com/exiftool/exiftool · GPL / Artistic (Perl terms) · Perl
- **Stars / dates:** [5,230★](https://api.github.com/repos/exiftool/exiftool) · last commit 2026-10-28 ✅
- **What it finds:** **EXIF, GPS, IPTC, XMP, and maker notes** in image, audio, video, and document files: GPS coordinates, camera and phone model, serial numbers, timestamps, software, and author.

#### OnionSearch (dark web)
- **Link:** https://github.com/megadose/OnionSearch · GPL-3.0 · Python
- **Stars / dates:** [1,834★](https://api.github.com/repos/megadose/OnionSearch) · last commit 2023-12-29 · last push 2024-08-08 ❌
- **Key / login:** None. It needs a running **Tor** proxy.
- **What it finds:** .onion URLs for a keyword, scraped from up to 16 onion search engines, including Ahmia, OnionLand, Phobos, Tor66, Tordex, Torgle, Haystack, and DeepLink. Install with `pip3 install onionsearch`. The README says it is for "educational purposes only".

#### Bellingcat auto-archiver (evidence preservation)
- **Link:** https://github.com/bellingcat/auto-archiver · docs https://auto-archiver.readthedocs.io/en/latest/ · MIT · Python
- **Stars / dates:** [1,142★](https://api.github.com/repos/bellingcat/auto-archiver) · last commit 2026-09-01 · last push 2026-09-10 ✅
- **Key / login:** Depends on configuration. For example, Google Sheets input or cloud storage needs credentials.
- **What it does:** Archives "social media posts, videos, images and webpages" from the URLs listed in a CSV, a Google Sheet, or on the CLI, "in a secure and verifiable way". It is an open-source alternative to Hunchly-style capture. Install with `pip install auto-archiver`, or use the Docker image `bellingcat/auto-archiver`.

### 2.6 Free transport and crypto tools

- **OpenSky Network** (aircraft): https://opensky-network.org/. Open ADS-B, Mode-S, ADS-C, FLARM, and VHF data "for research". Its [REST API](https://openskynetwork.github.io/opensky-api/rest.html) gives live **state vectors**, meaning position, altitude, velocity, callsign, squawk, and origin country by ICAO24 address or bounding box. It also has flights by aircraft or airport and tracks.
  - **Anonymous use:** 400 credits a day, current data only.
  - **Free account:** 4,000 credits a day and up to one hour of history via the API. Authentication uses OAuth2 client credentials.
- **ADS-B Exchange** (aircraft): https://globe.adsbexchange.com/. Free live map with **unfiltered** tracks. The API is paid.
- **Global Fishing Watch** (vessels): https://globalfishingwatch.org/our-map/. **"Free for everyone"** map of fishing activity and vessel presence from AIS and VMS data, plus **vessel encounters** and night-light vessel detections.
  - Covers **2012 to three days before today** and about 70,000 publicly trackable fishing vessels.
  - Vessel search works **without a login**. Free registration adds vessel tracks, events, and downloadable reports.
- **mempool.space** (Bitcoin explorer): https://mempool.space/ · source https://github.com/mempool/mempool. **AGPL-3.0**, [2,880★](https://api.github.com/repos/mempool/mempool), last commit 2026-11-01 ✅. Look up BTC addresses, transactions, and blocks, and self-host it for private lookups.
- **Etherscan** (Ethereum explorer, free, proprietary): https://etherscan.io/. Search by address, transaction, token, **name tag, label**, or domain name. Public labels such as exchange wallets and "Fake_Phishing" tags help with attribution.

### 2.7 Directories and distributions (not tools themselves)
- **OSINT Framework:** https://osintframework.com/ · source https://github.com/lockfale/OSINT-Framework. MIT, [12,374★](https://api.github.com/repos/lockfale/OSINT-Framework), last commit 2026-10-23 ✅.
- **awesome-osint:** https://github.com/jivoi/awesome-osint. [30,632★](https://api.github.com/repos/jivoi/awesome-osint), last commit 2026-10-31 ✅.
- **cipher387 OSINT tool collection:** https://github.com/cipher387/osint_stuff_tool_collection. GPL-3.0, [9,031★](https://api.github.com/repos/cipher387/osint_stuff_tool_collection), last commit 2026-11-01 ✅.
- **Kali Linux tools:** https://www.kali.org/tools/ (packages theHarvester, Recon-ng, SpiderFoot, Metagoofil, Sherlock, and others).
- **Bellingcat resources:** https://www.bellingcat.com/resources/

### 2.8 Free but NOT open source
- **Maltego Graph Community Edition** and **Lampyre** are free to start but proprietary. See Section 3 for what each one finds and costs.

---

## 3. Commercial and freemium OSINT platforms

Each price links to the page it was copied from (checked Nov 1–2, 2026). Free tools from Section 2 are not repeated here.

| Platform | Link | Free? / key | What it finds / key data | Sources |
|---|---|---|---|---|
| **Maltego** | https://www.maltego.com/ | **Basic €0/yr** (Graph CE, 200 credits a month). Entry €3,000/yr. Professional €7,500/yr. Enterprise custom ([pricing](https://www.maltego.com/pricing/)) | Link-analysis graphs from email, alias, phone, name, or domain. The **Data Pass** adds social profiles, breached credentials, phone, domain, crypto, corporate, and dark-web data. Hunchly is included from Entry up | 100+ connectors (third-party transforms using your keys) and vetted providers |
| **Lampyre** | https://lampyre.io/ | Paid credits ("Photons") with free sign-up ([site](https://lampyre.io/)) | "More than 100 requests for obtaining and processing data" from "more than 100 regularly updated data sources", shown on a map, graph, and table with timeline analysis. Its own example query is an email → linked accounts and breaches. Python API, AI agent, MCP server. The homepage does not list every input type | Aggregated third-party sources |
| **Shodan** | https://www.shodan.io/ | Free account (limited API). **Membership $49 one-time.** Freelancer $69/mo. Small Business $359/mo. Corporate $1,099/mo ([billing](https://account.shodan.io/billing)) | Internet-connected devices: open ports, banners, software, CVE filter (higher plans), screenshots, DNS, monitoring, firehose. Free keyless InternetDB via uncover's `shodan-idb` | Shodan's own scanners |
| **Censys** | https://censys.com/ | Free account. Paid plans use credits ([pricing](https://censys.com/resources/pricing/)) | Hosts, services, **certificates**, web properties, attack-surface management | Internet-wide scans, CT logs |
| **Intel 471** (owns SpiderFoot) | https://www.intel471.com/ | Enterprise | Cyber-underground intelligence; attack-surface products built on SpiderFoot | Underground forums and markets, OSINT |
| **Recorded Future** ([Mastercard-owned since Dec 2024](https://newsroom.mastercard.com/news/press/2024/december/mastercard-finalizes-acquisition-of-recorded-future/)) | https://www.recordedfuture.com/ | Enterprise | Threat, brand, and attack-surface intel; owns SecurityTrails | Open web, dark web, technical sources |
| **SecurityTrails** | https://securitytrails.com/ | Free account (50 API queries). Professional $500/mo. Business $1,500/mo ([pricing](https://securitytrails.com/corp/pricing)) | **Historical DNS (back to 2008)**, current and historical WHOIS, reverse WHOIS, subdomains, associated domains | Passive DNS, WHOIS, CT |
| **ZoomEye / FOFA / Netlas** | https://www.zoomeye.ai/ · https://en.fofa.info/ · https://netlas.io/ | Free tiers plus paid (key) | Internet asset search: hosts, services, components, certificates, DNS, WHOIS | Own scanning |
| **GreyNoise** | https://www.greynoise.io/ | **Free Community API** ([docs](https://docs.greynoise.io/reference/getcommunityip)) plus enterprise | Whether an IP is **mass-scanning ("noise")** or a known benign service ("RIOT"), classification, last seen | Global sensor network |
| **VirusTotal** | https://www.virustotal.com/ | Free public API, rate-limited ([public vs premium](https://docs.virustotal.com/reference/public-vs-premium-api)) | AV verdicts, passive DNS, relationships, and WHOIS for files, URLs, domains, and IPs | AV engines, submissions |
| **urlscan.io** | https://urlscan.io/ | Free plus paid | Page screenshots, requests, IPs, domains, technologies, phishing verdicts | Live scans |
| **Hunter.io** | https://hunter.io/ | Free plan plus paid ([pricing](https://hunter.io/pricing)) | **Work emails for a domain**, email finder, verification | Public web |
| **Have I Been Pwned** | https://haveibeenpwned.com/ | Free single search and alerts. **API key is paid** ([API docs](https://haveibeenpwned.com/API/v3)) | Breaches an email appears in (**1,048 breached sites / 17.8 billion accounts** per the [homepage counters](https://haveibeenpwned.com/), Nov 2, 2026), data classes, pastes, stealer-log domains. Free **Pwned Passwords** k-anonymity API | Verified breach corpora |
| **Intelligence X** | https://intelx.io/ | Limited free plus paid | Search by **email, domain, URL, IP/CIDR, phone, BTC/ETH address, IBAN**, and more, with historical copies ([buckets](https://help.intelx.io/api/bucket/)) | Tor/I2P, pastes, leaks, stealer logs, WHOIS, Usenet, web |
| **DeHashed** | https://dehashed.com/ | Paid (free preview) | Breach records by username, email, IP, name, address, phone, or hash; historical and reverse WHOIS | Leaks |
| **OSINT Industries** | https://www.osint.industries/ | **Basic £19/mo (30 credits).** Intermediate £49/mo. Advanced £99/mo ([pricing](https://www.osint.industries/pricing)) | Real-time **email, phone, username, name, crypto-wallet, IP, domain, and image** lookups → linked accounts and profile data | Live module checks (from the makers of holehe) |
| **Epieos** | https://epieos.com/ | Free (limited). **OSINTer from €30/mo** ([features](https://epieos.com/blog/features/how-to-use-epieos-for-your-osint-investigations)) | **Reverse email and phone**: Google account, linked profiles, name, Maps reviews, PGP key | Live platform checks |
| **Pipl** | https://pipl.com/ | Enterprise | Identity resolution and fraud intelligence | Proprietary identity graph |
| **Social Links** | https://sociallinks.io/ | Paid ([SL Crimewall](https://sociallinks.io/products/sl-crimewall)) | Social-media, dark-web, blockchain, and corporate intel; link analysis | Social networks, messengers, registries |
| **ShadowDragon** | https://shadowdragon.io/ | Paid | Public-information collection, identity triage, monitoring, SocialNet API | Hundreds of platforms |
| **Skopenow** | https://www.skopenow.com/ | Paid | Entity reports, link analysis, location analytics, fraud signals | Social, web, public records |
| **Babel Street / Dataminr / Fivecast / Liferaft / OSINT Combine** | https://www.babelstreet.com/ · https://www.dataminr.com/ · https://www.fivecast.com/ · https://liferaftlabs.com/ · https://www.osintcombine.com/ | Enterprise | Multilingual identity and risk intel; real-time event alerts; national-security OSINT; threat monitoring; OSINT search and training | Public and commercially available data |
| **Hunchly** | https://hunch.ly/ | Free trial, then paid | **Evidence capture**: saves every page visited with URL, timestamp, and hash (OSS alternative: auto-archiver, §2.5) | Your own browsing |
| **PimEyes** | https://pimeyes.com/ | Free (limited). Paid Open Plus, PROtect, Advanced ([pricing](https://pimeyes.com/en/pricing)) | **Face search**: web pages that publish a matching face, alerts | Crawled public images |
| **FaceCheck.ID** | https://facecheck.id/ | Pay-per-credit | Face search across social media, news, videos, mugshots | Crawled public images |
| **Google Lens / Bing Visual Search / Yandex / TinEye** | https://search.google/ways-to-search/lens/ · https://www.bing.com/images (camera icon; [how-to](https://support.microsoft.com/en-us/bing/using-bing-visual-search)) · https://yandex.com/images/ · https://tineye.com/ | Free | **Reverse image search**: copies, similar images, objects, landmarks | Engine indexes |
| **MarineTraffic / VesselFinder** | https://www.marinetraffic.com/ · https://www.vesselfinder.com/ | Free map plus paid | Live and historical vessel positions, port calls, ship database | AIS |
| **Flightradar24** | https://www.flightradar24.com/ | Free plus subscriptions | Live flights, history, aircraft data | ADS-B, MLAT |
| **OpenCorporates** | https://opencorporates.com/ | Free search plus paid API | Company records from **140+ jurisdictions** ([site](https://opencorporates.com/)) | Official registries |
| **Companies House / SEC EDGAR / GLEIF / OpenSanctions** | https://find-and-update.company-information.service.gov.uk/ · https://www.sec.gov/edgar/search/ · https://www.gleif.org/ · https://www.opensanctions.org/ | Free | Officers, filings, LEIs, ownership, **sanctions and PEPs** | Official registries |
| **Spokeo / Social Catfish** (US) | https://www.spokeo.com/ · https://socialcatfish.com/ | Paid | People search by name, phone, email, address, photo | US records and brokers |
| **Truecaller** | https://www.truecaller.com/ | Free app plus premium | Caller-ID name, spam reports | Crowdsourced contacts |
| **Ahmia / crt.sh / Wayback / DNSDumpster / ViewDNS** | https://ahmia.fi/ · https://crt.sh/ · https://web.archive.org/ · https://dnsdumpster.com/ · https://viewdns.info/ | Free | Tor search; CT-log certificates; archived pages; DNS maps; reverse IP and WHOIS | Tor, CT logs, crawls, DNS |

---

## 4. Comparison table: open-source and source-available tools

Commercial platforms are in Section 3 only. **Key / login:** **none** = works out of the box · **optional** = works without a key, does more with one · **free key** = free account or API key needed · **paid** = paid API needed · **cookies** = a logged-in session cookie is needed.

| Tool | Link | Licence | Category | Inputs | Data collected | Key / login | Status |
|---|---|---|---|---|---|---|---|
| SpiderFoot | https://github.com/smicallef/spiderfoot | MIT | Framework | IP, domain, host, CIDR, ASN, email, phone, username, name, BTC | Subdomains, DNS, emails, phones, names, crypto, threat intel, breaches, accounts, buckets, dark web, ports | optional | ❌ 2023-11-05 |
| Recon-ng | https://github.com/lanmaster53/recon-ng | GPL-3.0 | Framework | Domain, company, netblock, contact, location | Hosts, contacts, credentials, profiles, geotagged media, vulns (109 modules) | free key (many modules) | ✅ 2026-10-05 |
| theHarvester | https://github.com/laramies/theHarvester | GPL-2.0 | Domain recon | Domain, org | Subdomains, emails, IPs, ASNs, URLs | optional | ✅ 2026-10-20 |
| IntelOwl | https://github.com/intelowlproject/IntelOwl | AGPL-3.0 | Threat intel | IP, domain, URL, hash, file | Reputation, malware analysis, MISP/OpenCTI export | free key (per analyzer) | ✅ 2026-09-02 |
| DataSploit | https://github.com/DataSploit/datasploit | GPL-3.0 | Framework | Domain, email, IP, username | Credentials, API keys, subdomains, domain history | free key (config) | 🟡 2025-11-20 |
| FinalRecon | https://github.com/thewhiteh4t/FinalRecon | MIT | Web recon | URL, domain | Headers, WHOIS, SSL, crawl, DNS, subdomains, Wayback, ports | optional | ✅ 2026-10-31 |
| reNgine | https://github.com/yogeshojha/rengine | GPL-3.0 | Recon pipeline | Domain | Subdomains, IPs, ports, endpoints, screenshots, WHOIS, WAF, vulns, employees, emails, dorks | optional (OpenAI for GPT) | 🟡 2025-11-16 |
| Osmedeus | https://github.com/j3ssie/osmedeus | MIT | Recon pipeline | Domain, IP, list | Workflow outputs: assets, ports (nmap), CDN/WAF, vulns | none (wrapped tools vary) | ✅ 2026-10-04 |
| sn0int | https://github.com/kpcyrd/sn0int | GPL-3.0 | Framework | Domain, IP, email, phone, account | Subdomains, ASN/GeoIP, PGP/WHOIS emails, breached logins, profiles, images | none (core) | ✅ 2026-09-20 |
| Sherlock | https://github.com/sherlock-project/sherlock | MIT | Username | Username | Profile URLs on 481 sites | none | ✅ 2026-11-01 |
| Maigret | https://github.com/soxoj/maigret | MIT | Username dossier | Username | Accounts on 5,900 sites, profile data, linked IDs, recursion | none | ✅ 2026-10-29 |
| WhatsMyName | https://github.com/WebBreacher/WhatsMyName | CC BY-SA 4.0 (data) | Username dataset | Username | Existence on 692 sites | none | ✅ 2026-10-30 |
| Blackbird | https://github.com/antoniaci/blackbird | ⚠️ **none (source-available)** | Username / email | Username, email | Accounts on 600+ platforms, PDF | none (AI: free key) | ✅ 2026-10-17 |
| Social-Analyzer | https://github.com/qeeqbox/social-analyzer | AGPL-3.0 | Username / profile | Username, name | Profiles on 1000+ sites, confidence score, screenshots | none | 🟡 2026-01-12 |
| socialscan | https://github.com/iojw/socialscan | MPL-2.0 | Username / email | Username, email | Available/taken on 11 platforms | none | ❌ 2024-01-21 |
| Instaloader | https://github.com/instaloader/instaloader | MIT | Instagram | Profile, hashtag, location | Posts, stories, comments, geotags, captions, name changes | none (login for private) | ✅ 2026-11-01 |
| Osintgram | https://github.com/Datalux/Osintgram | GPL-3.0 | Instagram | IG account | Followers, captions, hashtags, geotag map, timing, contacts | paid (HikerAPI) or IG login | ✅ 2026-10-26 |
| Toutatis | https://github.com/megadose/toutatis | GPL-3.0 | Instagram | IG username or ID | Profile fields, public and obfuscated email/phone | cookies (sessionid) | ❌ 2024-12-05 |
| snscrape | https://github.com/JustAnotherArchivist/snscrape | GPL-3.0 | Social scraping | Username, query | (was) posts from 8 networks | none | ❌ 2023-06-22 |
| Twint | https://github.com/twintproject/twint | MIT | Twitter/X | Username, query | (was) tweets, followers | none | ❌ archived |
| Mr.Holmes | https://github.com/Lucksi/Mr.Holmes | GPL-3.0 | Multi | Domain, username, phone | Public-source hits, WHOIS, Google dorks (incl. media and date range) | optional (WhoisXMLAPI) | 🟡 2026-02-21 |
| OctoSuite | https://github.com/bellingcat/octosuite | MIT | GitHub OSINT | User, org, repo, search term | Profiles, followers, gists, events, commits, stargazers, members | none | ✅ 2026-10-26 |
| holehe | https://github.com/megadose/holehe | GPL-3.0 | Email → accounts | Email | Registered on 120+ sites, partial recovery email/phone | none | ❌ 2024-09-10 |
| GHunt | https://github.com/mxrch/GHunt | AGPL-3.0 | Google OSINT | Email, Gaia ID, Drive ID, BSSID | Google account, Gaia ID, Maps reviews, Calendar, Play Games, photo | cookies (Google) | 🟡 2026-04-10 |
| mosint | https://github.com/alpkeskin/mosint | MIT | Email | Email | Verification, social accounts, breaches, related domains, pastes, DNS | free/paid keys (config required) | ❌ 2023-09-19 |
| h8mail | https://github.com/khast3x/h8mail | BSD-3-Clause | Breach hunting | Email (plus others) | Breach hits, passwords and hashes via APIs or local dumps | paid | ❌ 2022-06-25 |
| PhoneInfoga | https://github.com/sundowndev/phoneinfoga | GPL-3.0 | Phone | Phone number | Country, carrier, line type, web footprint | optional | ✅ 2026-08-25 (author: "unmaintained") |
| TG phone checker | https://github.com/bellingcat/telegram-phone-number-checker | MIT | Phone → Telegram | Phone | Telegram username, name, ID | free key (Telegram API ID + account) | ✅ 2026-08-17 |
| ignorant | https://github.com/megadose/ignorant | GPL-3.0 | Phone → accounts | Phone | Used on Snapchat, Instagram, Amazon | none | ❌ 2023-12-29 |
| OWASP Amass | https://github.com/owasp-amass/amass | Apache-2.0 | Attack surface | Domain, ASN, CIDR | Subdomains, IPs, ASNs, network graph | optional | ✅ 2026-10-25 |
| Subfinder | https://github.com/projectdiscovery/subfinder | MIT | Subdomains | Domain | Passive subdomains | optional | ✅ 2026-10-31 |
| uncover | https://github.com/projectdiscovery/uncover | MIT | Search-engine aggregator | Query, IP/CIDR | Exposed hosts from 19 engines | free/paid keys (`shodan-idb`: none) | ✅ 2026-10-27 |
| Shodan CLI | https://github.com/achillean/shodan-python | MIT | Internet-scan client | IP, query | Banners, ports, vulns | free key | ❌ 2023-12-17 (stable) |
| dnstwist | https://github.com/elceef/dnstwist | Apache-2.0 | Lookalike domains | Domain | Registered permutations, phishing similarity, rogue MX, GeoIP | none | ❌ 2025-04-15 |
| gau | https://github.com/lc/gau | MIT | Historical URLs | Domain | URLs from OTX, Wayback, Common Crawl, URLScan | none | ✅ 2026-10-12 |
| waybackurls | https://github.com/tomnomnom/waybackurls | none declared | Historical URLs | Domain | Wayback URLs | none | ❌ 2022-04-05 |
| Sublist3r | https://github.com/aboul3la/Sublist3r | GPL-2.0 | Subdomains | Domain | Subdomains | none | ❌ 2020-07-29 |
| Photon | https://github.com/s0md3v/Photon | GPL-3.0 | Crawler | URL | URLs, emails, social accounts, buckets, secrets, JS endpoints | none | ❌¹ code 2019-12-06 |
| Metagoofil (opsdisk) | https://github.com/opsdisk/metagoofil | GPL-3.0 | Documents | Domain | Public docs for metadata | none | ✅ 2026-10-31 |
| ExifTool | https://exiftool.org/ | GPL / Artistic | Metadata | File | EXIF, GPS, IPTC, XMP, maker notes | none | ✅ 2026-10-28 |
| OnionSearch | https://github.com/megadose/OnionSearch | GPL-3.0 | Dark web | Keyword | .onion URLs from 16 engines | none (Tor) | ❌ 2023-12-29 |
| auto-archiver | https://github.com/bellingcat/auto-archiver | MIT | Archiving | URL list, Sheet | Archived posts, videos, images, pages | optional (per storage/source) | ✅ 2026-09-01 |
| mempool | https://github.com/mempool/mempool | AGPL-3.0 | BTC explorer | Address, tx, block | Balances, transactions | none | ✅ 2026-11-01 |
| OSINT Framework | https://github.com/lockfale/OSINT-Framework | MIT | Directory | — | Links to resources | none | ✅ 2026-10-23 |

---

## 5. "What data can be collected" matrix by input type

| Input you have | Data you can typically get | Best free / OSS tools | Best commercial / freemium |
|---|---|---|---|
| **Full name** | Social profiles, employers, directorships, registry records, news, photos, likely usernames and emails | SpiderFoot, Social-Analyzer, Google dorks, OpenCorporates and Companies House, OpenSanctions | OSINT Industries, Pipl, Skopenow, Spokeo (US), Maltego |
| **Username** | Accounts on hundreds to thousands of sites, bios, photos, linked IDs, posts, followers, geotags | **Maigret**, **Sherlock**, WhatsMyName, Blackbird, Social-Analyzer, socialscan, Instaloader / Osintgram / Toutatis (Instagram), OctoSuite (GitHub) | OSINT Industries, Social Links, ShadowDragon |
| **Email** | Registered sites, Google account, breaches, pastes, partial recovery phone or email, PGP keys | **holehe**, **GHunt**, Blackbird, socialscan, mosint, h8mail, sn0int | **HIBP**, **Epieos**, OSINT Industries, IntelX, DeHashed, Hunter.io |
| **Phone** | Country, carrier, line type; Telegram, Snapchat, Instagram, and Amazon presence; caller-ID name; web mentions | **PhoneInfoga**, **TG checker**, **ignorant**, Mr.Holmes, SpiderFoot | Epieos, OSINT Industries, Truecaller, IntelX |
| **Domain** | Subdomains, DNS, CT certs, WHOIS, emails, employees, documents and metadata, **lookalike domains**, **historical URLs** | **Amass**, **Subfinder**, **theHarvester**, **dnstwist**, **gau**/waybackurls, Metagoofil + ExifTool, FinalRecon, reNgine/Osmedeus, crt.sh | SecurityTrails, Censys, Shodan, VirusTotal, Hunter.io, IntelX |
| **IP / CIDR / ASN** | Ports, banners, versions, CVEs, certs, reverse IP, ASN, geolocation, reputation, "noise" | uncover (keyless `shodan-idb`), Shodan CLI, IntelOwl, SpiderFoot, Amass, sn0int | **Shodan**, **Censys**, GreyNoise, FOFA, ZoomEye, Netlas |
| **Image / photo** | EXIF GPS and camera, other copies online, face matches, landmarks, time of day from shadows | **ExifTool**, [SunCalc](https://www.suncalc.org/), [EO Browser](https://apps.sentinel-hub.com/eo-browser/), free Google Lens, Bing, Yandex, and TinEye | **PimEyes**, **FaceCheck.ID**, OSINT Industries (image) |
| **Company** | Officers, shareholders, filings, LEI, sanctions and PEP status, domains, employee emails | Recon-ng (`companies-*`), theHarvester, OpenCorporates search, Companies House, EDGAR, GLEIF, OpenSanctions | OpenCorporates API, Maltego, Babel Street, Hunter.io |
| **Crypto wallet** | Balance, transaction graph, labelled entities, leak and dark-web mentions | **mempool.space** (BTC, OSS), **Etherscan** (ETH, free), SpiderFoot extraction | OSINT Industries, IntelX, Maltego Data Pass |
| **Vessel / aircraft** | Live and historical position, route, encounters, port visits | **OpenSky** (free API), **ADS-B Exchange** free map, **Global Fishing Watch** free map | MarineTraffic, VesselFinder, Flightradar24, ADS-B Exchange API |
| **Keyword (dark web)** | .onion pages mentioning it | **OnionSearch**, Ahmia | Intelligence X, Intel 471 |
| **URL (preserve evidence)** | Archived copy with hash and timestamp | **auto-archiver**, Wayback Machine | Hunchly |

---

## 6. Legal reference note (summary, not legal advice)

| Jurisdiction / law | Provisions relevant to OSINT work | Source |
|---|---|---|
| **Pakistan: PECA 2016** (Act XL of 2016) | **s.3** unauthorised access to an information system or data: up to 3 months and/or PKR 50,000. **s.16** obtaining, selling, possessing, transmitting, or using another person's identity information without authorisation: up to 3 years and/or PKR 5 million. **s.24 cyberstalking**: using electronic means, with intent to coerce, intimidate, or harass, to repeatedly contact, monitor, or watch a person, or to share their photo or video without consent. Up to 3 years and/or PKR 1 million (5 years / PKR 10 million if the victim is a minor) | [s.3](https://statutes.pk/peca/3) · [s.16](https://statutes.pk/peca/16) · [s.24](https://statutes.pk/peca/24) · [MoITT legislation list](https://www.moitt.gov.pk/Legislations) |
| **Pakistan: PECA (Amendment) Act 2025** (Act II of 2025) | Presidential assent on 29 Jan 2025. Adds new definitions, a Social Media Protection and Regulatory Authority, and a false-information offence | [HRCP analysis with gazette text](https://hrcp-web.org/hrcpweb/wp-content/uploads/2020/09/2025-LWC10-PECA-Amendment-Act-2025.pdf) · [Gazette copy on na.gov.pk](https://www.na.gov.pk/uploads/documents/679b243193585_457.pdf) |
| **Pakistan: Personal Data Protection Bill** | **Still a draft.** MoITT lists drafts dated July 2018, April 2020, and May 2023, each with status "Draft". A 2023 Senate private member's bill was withdrawn | [MoITT](https://www.moitt.gov.pk/Legislations) · [Senate bill record](https://www.senate.gov.pk/en/billsummary.php?bid=1182) |
| **EU: GDPR** | Personal data needs a lawful basis even when public. Biometric data used to identify a person is a special category (**Art. 9**) | Baden-Württemberg LfDI, below |
| **EU example: PimEyes** | The Baden-Württemberg data-protection authority (LfDI) opened proceedings against PimEyes after 2021 media reports. It received PimEyes' response on 1 Nov 2022 and announced **fine proceedings (Bußgeldverfahren) on 21 Dec 2022**, citing Art. 9 GDPR (biometric data) and Art. 25(2) (the opt-out design). The outcome was not checked for this report | [LfDI press release (German)](https://www.baden-wuerttemberg.datenschutz.de/pimeyes-lfdi-eroeffnet-bussgeldverfahren/) |
| **US: CFAA**, 18 U.S.C. §1030 | Covers accessing a computer without authorisation or exceeding authorised access. Relevant to active scanning and logins beyond public pages | [Cornell LII](https://www.law.cornell.edu/uscode/text/18/1030) · [DOJ manual](https://www.justice.gov/jm/jm-9-48000-computer-fraud) |
| **UK: Computer Misuse Act 1990** | s.1 makes unauthorised access to computer material an offence. Relevant to active scanning or probing systems you don't own | [legislation.gov.uk](https://www.legislation.gov.uk/ukpga/1990/18/contents) |

**How this maps to the tools:** Active steps (port scans, DNS brute force, direct probing in theHarvester, reNgine, Osmedeus, FinalRecon, SpiderFoot) are normally run only on systems you own or are authorised to test; people-focused tools (username, email, phone, face) touch PECA s.16 and s.24 (cyberstalking) and GDPR when used to profile or track an individual; login- or cookie-based scrapers (Osintgram, Toutatis, Instaloader `--login`, GHunt) are subject to platform terms, and breach data (h8mail, DeHashed, IntelX) falls under s.16-type identity-information rules.

---

## 7. Sources (all checked Nov 1–2, 2026)

**GitHub repositories** (metadata via `https://api.github.com/repos/<owner>/<repo>`; last commit via `/commits.atom`):
- https://github.com/smicallef/spiderfoot · https://github.com/smicallef/spiderfoot/tree/master/modules
- https://github.com/lanmaster53/recon-ng · https://github.com/lanmaster53/recon-ng-marketplace · https://raw.githubusercontent.com/lanmaster53/recon-ng-marketplace/master/modules.yml
- https://github.com/laramies/theHarvester
- https://github.com/intelowlproject/IntelOwl
- https://github.com/DataSploit/datasploit
- https://github.com/thewhiteh4t/FinalRecon
- https://github.com/yogeshojha/rengine
- https://github.com/j3ssie/osmedeus
- https://github.com/kpcyrd/sn0int
- https://github.com/sherlock-project/sherlock · https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json
- https://github.com/soxoj/maigret
- https://github.com/WebBreacher/WhatsMyName · https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json
- https://github.com/antoniaci/blackbird
- https://github.com/qeeqbox/social-analyzer
- https://github.com/iojw/socialscan
- https://github.com/instaloader/instaloader
- https://github.com/Datalux/Osintgram
- https://github.com/megadose/toutatis
- https://github.com/JustAnotherArchivist/snscrape
- https://github.com/twintproject/twint
- https://github.com/Lucksi/Mr.Holmes
- https://pypi.org/project/osrframework/
- https://github.com/bellingcat/octosuite
- https://github.com/megadose/holehe
- https://github.com/mxrch/GHunt · https://github.com/mxrch/GHunt/commits/master
- https://github.com/alpkeskin/mosint
- https://github.com/khast3x/h8mail
- https://github.com/sundowndev/phoneinfoga
- https://github.com/bellingcat/telegram-phone-number-checker
- https://github.com/megadose/ignorant
- https://github.com/owasp-amass/amass
- https://github.com/projectdiscovery/subfinder
- https://github.com/projectdiscovery/uncover
- https://github.com/achillean/shodan-python
- https://github.com/elceef/dnstwist
- https://github.com/lc/gau
- https://github.com/tomnomnom/waybackurls
- https://github.com/aboul3la/Sublist3r
- https://github.com/s0md3v/Photon · https://github.com/s0md3v/Photon/commits/master
- https://github.com/opsdisk/metagoofil · https://github.com/laramies/metagoofil
- https://github.com/exiftool/exiftool
- https://github.com/megadose/OnionSearch
- https://github.com/bellingcat/auto-archiver
- https://github.com/mempool/mempool
- https://github.com/lockfale/OSINT-Framework · https://github.com/jivoi/awesome-osint · https://github.com/cipher387/osint_stuff_tool_collection

**Official sites and docs:**
- https://www.intel471.com/company/press-releases/intel-471-acquires-spiderfoot
- https://www.maltego.com/pricing/ · https://lampyre.io/
- https://www.shodan.io/ · https://account.shodan.io/billing · https://help.shodan.io/command-line-interface/0-installation
- https://censys.com/ · https://censys.com/resources/pricing/
- https://www.recordedfuture.com/ · https://newsroom.mastercard.com/news/press/2024/december/mastercard-finalizes-acquisition-of-recorded-future/
- https://securitytrails.com/ · https://securitytrails.com/corp/pricing
- https://www.zoomeye.ai/ · https://en.fofa.info/ · https://netlas.io/
- https://www.greynoise.io/ · https://docs.greynoise.io/reference/getcommunityip
- https://www.virustotal.com/ · https://docs.virustotal.com/reference/public-vs-premium-api
- https://urlscan.io/ · https://hunter.io/ · https://hunter.io/pricing
- https://haveibeenpwned.com/ · https://haveibeenpwned.com/API/v3
- https://intelx.io/ · https://help.intelx.io/api/bucket/
- https://dehashed.com/ · https://www.osint.industries/ · https://www.osint.industries/pricing
- https://epieos.com/ · https://epieos.com/blog/features/how-to-use-epieos-for-your-osint-investigations
- https://pipl.com/ · https://sociallinks.io/ · https://sociallinks.io/products/sl-crimewall · https://shadowdragon.io/ · https://www.skopenow.com/
- https://www.babelstreet.com/ · https://www.dataminr.com/ · https://www.fivecast.com/ · https://liferaftlabs.com/ · https://www.osintcombine.com/ · https://hunch.ly/
- https://pimeyes.com/ · https://pimeyes.com/en/pricing · https://facecheck.id/
- https://search.google/ways-to-search/lens/ · https://www.bing.com/images · https://support.microsoft.com/en-us/bing/using-bing-visual-search · https://yandex.com/images/ · https://tineye.com/
- https://www.marinetraffic.com/ · https://www.vesselfinder.com/ · https://globalfishingwatch.org/our-map/
- https://opensky-network.org/ · https://openskynetwork.github.io/opensky-api/rest.html
- https://globe.adsbexchange.com/ · https://www.flightradar24.com/
- https://mempool.space/ · https://etherscan.io/
- https://opencorporates.com/ · https://find-and-update.company-information.service.gov.uk/ · https://www.sec.gov/edgar/search/ · https://www.gleif.org/ · https://www.opensanctions.org/
- https://www.spokeo.com/ · https://socialcatfish.com/ · https://www.truecaller.com/
- https://ahmia.fi/ · https://crt.sh/ · https://web.archive.org/ · https://dnsdumpster.com/ · https://viewdns.info/
- https://exiftool.org/ · https://www.kali.org/tools/libimage-exiftool-perl/ · https://www.suncalc.org/ · https://apps.sentinel-hub.com/eo-browser/
- https://osintframework.com/ · https://www.kali.org/tools/ · https://www.bellingcat.com/resources/
- https://whatsmyname.app/ · https://sherlockproject.xyz/ · https://maigret.readthedocs.io/ · https://sundowndev.github.io/phoneinfoga/ · https://intelowlproject.github.io/docs/
- https://owasp.org/projects/amass · https://www.osmedeus.org/ · https://instaloader.github.io/ · https://dnstwist.it/ · https://sn0int.com/ · https://auto-archiver.readthedocs.io/en/latest/

**Legal:**
- https://statutes.pk/peca/3 · https://statutes.pk/peca/16 · https://statutes.pk/peca/24
- https://www.moitt.gov.pk/Legislations · https://hrcp-web.org/hrcpweb/wp-content/uploads/2020/09/2025-LWC10-PECA-Amendment-Act-2025.pdf · https://www.na.gov.pk/uploads/documents/679b243193585_457.pdf · https://www.senate.gov.pk/en/billsummary.php?bid=1182
- https://www.baden-wuerttemberg.datenschutz.de/pimeyes-lfdi-eroeffnet-bussgeldverfahren/
- https://www.law.cornell.edu/uscode/text/18/1030 · https://www.justice.gov/jm/jm-9-48000-computer-fraud
- https://www.legislation.gov.uk/ukpga/1990/18/contents

*Note on blocked checks (final link check, Nov 2, 2026):* 193 of 203 unique URLs returned HTTP 200. One GitHub API record (iojw/socialscan) hit the unauthenticated rate limit (403); its data comes from an earlier successful call. The other nine are live sites that block or time out on scripted requests, not dead links:
- **403 (bot protection):** securitytrails.com (×2), epieos.com (×2), tineye.com, dataminr.com, sec.gov
- **Timed out from the check server:** intelx.io, opensky-network.org (the same page loaded fine through a web fetcher), and na.gov.pk (unreachable from the check server; it appears in search indexes, and the HRCP copy of the same gazette text is linked alongside it)

No 404s remain. github.com/i3visio/osrframework is mentioned only as text because it now ends in a 404.
