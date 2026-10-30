*Draft, needs review.*

# 19. Fingerprinting and Known CVEs

- **Phase:** No credentials (mapping)
- **Risk:** 🟢 Safe: single requests that read headers, titles and versions. 🟡 Noisy: informational nmap web scripts, TLS scans. 🔴 Risky: running any exploit or vulnerability scanner. Ask the client contact in writing first, every time, and log it.
- **Tier:** Must know
- **Finding:** library L22 (`outdated-software`)
- **Ports:** 80, 443, 8000, 8008, 8080, 8081, 8443, 8888, 9000
- **Tools:** httpx-toolkit, curl, whatweb, nmap; vendor advisories and public CVE records, checked offline
- **You need:** the list of web URLs from recon (`urls.txt`)

## What it is
Learn what each site runs (web server, framework, CMS, plugins) and which exact version. An old version with a published CVE is a finding on its own, and often the shortest way in.

**How often:** outdated or unsupported software appeared in at least five of the six recent CPTC environments we reviewed.

⚠️ **A version is a lead, not proof.**
- Linux distributions backport fixes without changing the version string.
- Report version-only evidence as Suspected until a check confirms it.

**Fix to recommend:** update to a supported version; remove version banners from headers and error pages.

**Pattern: fingerprint, look up the exact version offline, then ask before testing the CVE.**

**Checklist:** `checklists/20-web-app.md` (Map it: Fingerprint the stack and versions).

## Commands
1. Which URLs respond, with title, status and technology: `httpx-toolkit -l urls.txt -title -status-code -tech-detect -rate-limit 10 -duc` 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: one line per URL with its status, page title and detected technologies.
2. Headers of one page: `curl -sI http://<host>:<port>/` 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: `Server`, `X-Powered-By` or similar headers, sometimes with a version.
3. Fingerprint the technology: `whatweb http://<host>:<port>` 🟢 (default aggression only; `-a 3` and `-a 4` are 🟡) [[NOTE: from the Recon Field Guide]]
   Expected: the CMS, framework, server and versions it can see.
4. Informational web scripts: `nmap -n -p 80,443 --script http-title,http-headers,http-methods <host>` 🟡 [[NOTE: from the Recon Field Guide]]
   Expected: page titles, headers and the HTTP methods allowed.
5. Look up each exact version offline: vendor advisories, the CVE record, CISA's Known Exploited Vulnerabilities list. Note the CVE and the fixed version.
   Expected: a CVE that matches the exact version, or none.
6. [[TODO: Add a non-destructive check for a specific CVE only after its command and rating are in the Recon Field Guide. Running the exploit is 🔴 Risky: ask the client contact in writing first, every time, and log it.]]
   Expected: Applicability confirmed without running the exploit, or the status stays Suspected.

## Evidence to capture
- `evidence/F-NNN-01.txt`: the header, banner or whatweb output showing the exact version, with the host and timestamp.
- The CVE ID, the vendor advisory link and the fixed version.
- Whether the finding is Suspected (version only) or Confirmed.

## Practice
- [[TODO: Pick a retired HTB web box with an outdated CMS, and practise fingerprint → CVE lookup without running the exploit.]]

---
*Written by the CCSF 2026 team from past-CPTC environment research.*
