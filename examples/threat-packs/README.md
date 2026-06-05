# Threat Packs

Curated, tuned-for-low-false-positive rule sets covering the most common
Threat Intelligence and OSINT scenarios on Telegram. Each pack is a drop-in
partial config - pick what you need, paste into your `config.json`'s
`rules[]` array, optionally tune excludes, and you're live.

> **Quality bar.** Every rule was designed around three principles:
> **(1) multi-signal lookahead regex** - require co-occurrence of a target
> term AND a transaction/context term in the same message, not single
> keywords; **(2) discriminating vocabulary** - prefer rare jargon over
> generic words ("FUD exploit", "AitM panel", "domain admin access for
> sale") to suppress benign noise; **(3) sharp excludes** for the dominant
> false-positive sources (vendor advisories, news outlets like KrebsOnSecurity
> / BleepingComputer / TheHackerNews, research blogs from Mandiant /
> CrowdStrike / Talos / Project Zero, CTF/training/lab content).
>
> All packs were corpus-tested with true-positive and false-positive samples
> before shipping. The targets: **100% recall on TP samples, ≥95% specificity
> on FP samples.**

---

## Quick start

1. Open the pack you want (e.g. `cve-chatter.json`).
2. Copy the rule objects from the `rules[]` array.
3. Paste them into your `config.json`'s `rules[]` array.
4. (Optional) Use the TUI: `telescope config` → Rules tab → paste each rule.

Tag convention used by every pack:

- `severity:critical|high|medium|low` - turns into `[CRITICAL]` / `[HIGH]` /
  `[MED]` / `[LOW]` prefix in the alert header
- `category:<name>` - coarse grouping for downstream filtering
- `mitre:T<id>` - MITRE ATT&CK technique mapping (informational; not enforced)
- `actor-class:<name>` - actor classification where applicable (e.g.
  `nation-state` on zero-click rules)

The pack files also include metadata fields (`_description`, `_fp_risk`,
`_severity_rationale`) on every rule. The runtime engine silently ignores
unknown keys - these are pure documentation for you.

---

## Pack catalogue

### 1. `0day-marketplace.json` - 0-day & exploit marketplace
**5 rules. Severity: critical–high.**

| Rule | What it catches |
|---|---|
| `0day - direct sale offer` | Private/weaponized exploit sale with explicit transactional signal (price, BTC/XMR, escrow, DM/PM contact, jabber, $X amount) |
| `0day - high-impact product chatter` | Working exploits against critical products (browsers, edge appliances, hypervisors, enterprise SaaS) - product + critical primitive (preauth RCE, sandbox escape, kernel, 0-click) |
| `0day - exploit broker / acquisition` | Buyer side: brokers (Crowdfense, Trenchant, Zerodium, SSD Labs) or actors soliciting exploits with payouts |
| `0day - public PoC / ITW` | Public weaponization - PoC released, exploit code dropped, Metasploit/Nuclei module merged, in-the-wild exploitation |
| `0day - 0-click exploit chatter` | Pegasus-class: 0-click / interaction-less RCE chains targeting iMessage, WhatsApp, Outlook, Teams |

**Use this pack if you:** monitor underground marketplaces, track exploit
broker activity, want early warning on weaponized vulnerabilities affecting
your stack.

---

### 2. `iab-listings.json` - Initial Access Broker listings
**5 rules. Severity: critical–high.**

| Rule | What it catches |
|---|---|
| `IAB - corporate access listing` | Sale of network access - VPN/RDP/SSH/Citrix/Fortinet/AD/webshell - with explicit transactional signal |
| `IAB - victim characterization (industry + revenue + access)` | Listings with the "US-based manufacturing company, revenue $200M" pattern that distinguishes real IAB ads from generic discussion |
| `IAB - corporate stealer logs / cookie shop` | Fresh credentials/cookies/sessions from infostealers, sorted for enterprise SSO (Okta, Azure AD, M365, Google Workspace, AWS, GCP) |
| `IAB - privileged account access for sale` | Domain admin, enterprise admin, global admin, AWS root, Kerberos golden/silver tickets |
| `IAB - webshell / panel access` | cPanel, WHM, Plesk, WordPress admin, application-tier access listings |

**Use this pack if you:** track corporate-targeting underground activity,
care about pre-ransomware kill-chain visibility, want stealer-log marketplace
intelligence.

---

### 3. `ransomware-leaks.json` - Ransomware operations
**4 rules. Severity: critical–high.**

| Rule | What it catches |
|---|---|
| `Ransomware - leak site posting` | Group-attributed victim disclosure - actor name + publication verb, or `.onion` link + leak/extortion context |
| `Ransomware - affiliate recruitment` | Pentester / affiliate / operator recruitment for RaaS programs with profit-share language |
| `Ransomware - extortion countdown` | Active extortion timers/deadlines/countdowns tied to publication threat |
| `Ransomware - RaaS builder / panel sale` | Sale of ransomware builders, panels, decryptors, RaaS subscriptions |

**Tracks: LockBit, Cl0p, BlackCat/ALPHV, Black Basta, Akira, Play, Royal,
Rhysida, 8base, Medusa, Qilin, Ragnar Locker, NoEscape, DragonForce,
RansomHub, Hunters International, Cactus, 3AM, Trinity, Sarcoma, FunkSec,
Kairos** (extensible - actor list lives in the regex).

**Use this pack if you:** monitor ransomware leak sites for sector or
victim mentions, track operational ecosystem (recruitment, RaaS
distribution).

---

### 4. `cve-chatter.json` - CVE & vulnerability signals
**4 rules. Severity: critical–high–low.**

| Rule | What it catches | Default |
|---|---|---|
| `CVE - bare mention` | Any `CVE-YYYY-NNNNN` ID mention | **disabled** (informational, generates volume) |
| `CVE - active exploitation / public PoC` | CVE/0-day + in-the-wild / weaponized / PoC released / Metasploit module merged | enabled |
| `CVE - high-impact product vulnerability` | Vendor product (Fortinet, Citrix, VMware, Exchange, Confluence, etc.) + critical vuln class (preauth RCE, auth bypass, SSRF, etc.) | enabled |
| `CVE - critical vulnerability class` | Preauth RCE / unauth code execution / auth bypass + disclosure/release context | enabled |

**Use this pack if you:** want to know about CVEs that crossed from
theoretical to weaponized, prioritize patching based on chatter signal,
track exploitation against your stack.

---

### 5. `credential-leaks.json` - Credential dumps & combolists
**4 rules. Severity: high.**

| Rule | What it catches |
|---|---|
| `Credentials - combolist drop / sale` | Combolist / user:pass / email:pass pair dumps with scale (`5M lines`), quality (UHQ/HQ/fresh), or sale intent |
| `Credentials - database leak / breach drop` | Full DB dumps, SQL dumps, "1M records leaked / for sale" patterns |
| `Credentials - session / cookie marketplace` | Valid cookies/sessions/JWT/OAuth tokens for high-value SaaS (Okta, Azure, GitHub, AWS, GCP, M365, Salesforce, Coinbase, Binance, Stripe) - including Genesis Market / Russian Market mentions |
| `Credentials - free public dump` | Free/public credential dumps without sale intent (broader-reach attacks) |

**Use this pack if you:** monitor credential-stuffing supply, watch
breach-disclosure cadence in underground vs. news, hunt for your own
domain in dumps.

---

### 6. `malware-raas.json` - Malware as a Service
**4 rules. Severity: critical–high–medium.**

| Rule | What it catches |
|---|---|
| `Malware - infostealer commercial chatter` | RedLine, Lumma, Vidar, Raccoon, Stealc, MetaStealer, Rhadamanthys, Aurora, Atomic/AMOS, RisePro, Azorult, Nexus, FormBook, Agent Tesla, SnakeKeylogger, HawkEye, Lokibot - paired with subscription/license/panel language |
| `Malware - loader / botnet commercial chatter` | SmokeLoader, Amadey, PrivateLoader, Gootloader, Bumblebee, Qakbot, Emotet, IcedID, TrickBot, Brute Ratel, Cobalt Strike (cracked), Sliver, Nighthawk, Havoc, Mythic - with commercial signals |
| `Malware - crypter / FUD builder` | Crypters, packers, FUD builders, runtime/scantime obfuscators, AV/EDR bypass tooling |
| `Malware - RAT / backdoor sale` | NjRAT, AsyncRAT, QuasarRAT, VenomRAT, Warzone, NanoCore, NetWire, Remcos, Orcus, DarkComet, XWorm, SpyNote, Cerberus, HookBot, Anatsa, Octo, TeaBot, Brokewell, Crocodilus |

**Phishing kits and AitM panels are in a separate pack** -
`phishing-infrastructure.json`.

**Use this pack if you:** track the malware-distribution ecosystem,
prioritize endpoint detection by what's actually being sold, want family-
name + commercial-context signal rather than analyst writeups.

---

### 7. `phishing-infrastructure.json` - Phishing & credential-theft delivery
**5 rules. Severity: critical–high–medium.**

| Rule | What it catches |
|---|---|
| `Phishing - kit / scampage sale` | Phishing kits, scampages, fake login pages cloned from M365/Office/Gmail/Outlook/bank - with sale/subscription language |
| `Phishing - AitM / MFA-bypass panel` | EvilGinx, EvilProxy, Tycoon 2FA, Mamba 2FA, Rockstar 2FA, Greatness, Muraena, Modlishka, Storm-1011 - plus generic AitM/2FA-bypass/cookie-capture jargon |
| `Phishing - letter sender / SMTP service` | Bulletproof SMTP, letter senders, mailers, cracked SendGrid/AWS SES, inbox-rate marketing |
| `Phishing - smishing / SMS infrastructure` | Smishing kits, bulk SMS gateways, spoofed SMS, SS7 services |
| `Phishing - typosquat / lookalike domain` | Just-registered lookalike / homograph / IDN-homograph / punycode domains, drop-catch services |

**Use this pack if you:** track phishing campaign infrastructure,
care about MFA-bypass tool spread, hunt for typosquats of your domains.

---

### 8. `brand-monitoring.json` - Your organization (TEMPLATE)
**5 rules. Severity: critical–high.**

> **This pack is a template.** Before enabling, search-and-replace these
> placeholders with your own identifiers:
> - `YOURBRAND` → your company name
> - `yourdomain.com`, `yourbrand.com` → your apex domains
> - `YourCEO`, `YourCFO`, `YourCTO`, `YourExec`, `YourFounder` → your executive
>   names

| Rule | What it catches |
|---|---|
| `Brand - YOURBRAND in leak/breach context` | Your name/domain + leak/breach/dump/exposed/for-sale language |
| `Brand - YOURBRAND in IAB context` | Your name + access-sale jargon (VPN access, domain admin, etc.) - high-confidence active-targeting signal |
| `Brand - executive impersonation / targeting` | Exec name + impersonation/deepfake/BEC/spoofed/doxx context |
| `Brand - YOURBRAND lookalike / typosquat domain` | Registered lookalike domains across common TLDs |
| `Brand - YOURBRAND customer database leak` | Your name + customer database / users DB / employee DB / SQL dump |

**Use this pack if you:** are an org defending its own brand - this is the
highest-ROI pack because it is yours.

**Important:** Test against your own corpus first. Some rules may fire on
your own marketing/PR feeds; add those to the per-rule exclude_keywords.

---

### 9. `supply-chain-compromise.json` - Software supply chain
**5 rules. Severity: critical–high.**

| Rule | What it catches |
|---|---|
| `Supply chain - malicious package upload` | npm/PyPI/RubyGems/Crates.io/Maven/NuGet/Composer/Go/CocoaPods + malicious/trojan/backdoor/cryptominer/wallet-stealer |
| `Supply chain - typosquat / dependency confusion package` | Registry-targeted typosquats, dependency-confusion exploits, lookalike packages |
| `Supply chain - maintainer / package hijack` | Compromised maintainer accounts, 2FA bypass on registry, malicious version push to legitimate package |
| `Supply chain - trojanized github repo / fake PoC` | Fake security tools, fake PoCs, trojanized "hack tools" - common attack vector against researchers |
| `Supply chain - install-script payload` | postinstall / preinstall / setup.py / install-hook payloads (silent execution with developer privileges) |

**Use this pack if you:** run a security or developer org, depend on
public registries, want early warning on supply-chain incidents that
typically broadcast in TI circles before vendor disclosure.

---

### 10. `ics-scada.json` - Industrial / OT / critical infrastructure
**5 rules. Severity: critical–high–medium.**

| Rule | What it catches |
|---|---|
| `ICS - operational ICS malware mention` | Industroyer/Industroyer2, Triton/Trisis, Havex, BlackEnergy, CrashOverride, Pipedream/INCONTROLLER, Fuxnet, IronGate, EKANS/SNAKE - and Stuxnet variants/source in commercial context |
| `ICS - vendor product vulnerability` | Siemens Simatic/WinCC/TIA, Schneider Modicon/EcoStruxure, Rockwell Logix/Allen-Bradley, Mitsubishi MELSEC, Honeywell Experion, Yokogawa Centum, GE Digital, Emerson Ovation, Phoenix Contact, Beckhoff TwinCAT, ABB - with vuln/exploit terms |
| `ICS - OT / plant network access for sale` | Direct sale of PLC/HMI/SCADA/RTU/OT-VPN/DCS/historian access |
| `ICS - exposed device enumeration` | Shodan/Censys/ZoomEye/FOFA/Onyphe/Hunter.how queries against ICS protocols (Modbus, DNP3, BACnet, S7Comm, EtherNet/IP, OPC UA, IEC 104, IEC 61850, Profinet, HART, Niagara Fox) |
| `ICS - critical infrastructure sector targeting` | Power grid, substation, gas/oil pipeline, refinery, water treatment, nuclear, hydroelectric, wind farm, district heating - paired with attack/breach/disrupt/sabotage/wiper language |

**Use this pack if you:** work in energy, utilities, manufacturing, oil &
gas, water, transportation - or sell to that sector. This is the rarest
high-portfolio-value pack.

---

## Engine internals (for the curious)

The Telescope rules engine is a flat keyword/regex matcher (`src/core/rules_engine.py`)
with Python's `re` module under the hood. Patterns can use the full Python
regex syntax - including `(?is)` inline flags (`i` = case-insensitive, `s` =
DOTALL so `.` matches newlines), lookaheads `(?=…)`, and named groups.

Two-signal lookaheads are the workhorse of this pack collection:

```python
(?is)(?=.*\b(TARGET_TERM)\b)(?=.*\b(CONTEXT_TERM)\b)
```

This matches when **both** TARGET_TERM and CONTEXT_TERM appear anywhere
in the same message (any order, any distance). Three-signal lookaheads
extend the same pattern to require three categories.

`exclude_keywords` is a **substring** matcher, not regex. Lowercase only.
Any single match in the message disqualifies the rule before the regex
runs. Use this for the cheapest, most discriminating FP-killers - vendor
names, news outlet names, CTF/training markers.

---

## Tuning advice

1. **Start with one or two packs**, see real-world signal volume in your
   environment, then add more. The whole catalogue at once may produce
   more alerts than you can triage.
2. **Watch for repeat FPs in your specific corpus.** Each pack ships with
   the broadly common excludes, but your monitored channels may have
   specific noise (a partner who keeps posting "selling tickets, DM me"
   in a sec channel, etc.). Add to `exclude_keywords` per rule.
3. **Severity is a starting recommendation.** Demote to `severity:medium`
   or below if a rule produces too much noise for your downstream pipeline.
4. **The `_description` and `_fp_risk` fields are documentation, not
   runtime config.** Read them before tweaking a rule - they explain the
   design intent so your changes don't undo the FP suppression.
5. **Submit improvements back.** If you find a strong exclude or a true-
   positive variant we missed, open a PR with the corpus sample that
   motivated the change.
