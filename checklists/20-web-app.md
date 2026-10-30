# Web / Patron Systems Run Sheet (ticketing, POS, guest apps)

> Background: which OWASP Top 10 category each web playbook covers is in playbooks/web/00-owasp-top-10.md.

## Map it
- [ ] List every web service from the nmap output (80, 443, 8080, 8443, and anything else that speaks HTTP)
- [ ] Proxy everything through Burp. Browse every feature as a normal user first. · 🟢 Safe (playbook: playbooks/general/03-unfamiliar-business-systems.md)
- [ ] Content discovery at a polite rate: `ffuf -u https://<host>/FUZZ -w <wordlist> -rate 20`
- [ ] Fingerprint the stack and versions → check known CVEs for those exact versions · 🟢 Safe / 🟡 Noisy / 🔴 Risky (playbook: playbooks/web/19-fingerprinting-known-cves.md)
- [ ] Look for `robots.txt`, `.git/`, backup files, API docs (`/swagger`, `/api/docs`), and default admin panels · 🟢 Safe / 🟡 Noisy (playbooks: playbooks/web/07-git-leakage.md, playbooks/web/01-unauthenticated-endpoint.md)

## Authentication and sessions
- [ ] Default and weak credentials on admin panels (check the ROE on brute force) · 🟡 Noisy / 🔴 Risky (playbook: playbooks/web/16-excessive-login-attempts.md)
- [ ] Username enumeration via login, reset, or registration messages · 🟡 Noisy (playbook: playbooks/web/15-username-enumeration-password-reset.md)
- [ ] Password reset flow: token predictability, reuse, host header injection · 🟡 Noisy / 🔴 Risky (playbook: playbooks/web/20-password-reset-flow.md)
- [ ] Session cookie flags, logout invalidation, fixation · 🟢 Safe (playbooks: playbooks/web/10-cookies-without-httponly.md, playbooks/web/11-cookies-without-secure.md, playbooks/web/08-hsts-not-enabled.md)

## Access control (the highest-yield area for patron systems)
- [ ] IDOR: change IDs in tickets, orders, profiles, and receipts (`/ticket/1001` → `1002`) · 🟢 Safe / 🔴 Risky (playbook: playbooks/web/18-idor-horizontal-access.md)
- [ ] Horizontal: can guest A see guest B's data? · 🟢 Safe / 🔴 Risky (playbook: playbooks/web/18-idor-horizontal-access.md)
- [ ] Vertical: can a guest reach staff or admin functions directly? · 🟢 Safe / 🔴 Risky (playbook: playbooks/web/14-forged-role-in-cookie.md)
- [ ] API endpoints the UI doesn't show · 🟢 Safe / 🟡 Noisy (playbooks: playbooks/web/01-unauthenticated-endpoint.md, playbooks/web/03-deprecated-api-endpoint.md, playbooks/web/06-readable-data-in-tokens.md)

## Injection
- [ ] SQLi in search, filters, and IDs (manual first; `sqlmap` only with a low `--risk`/`--level` and never against write endpoints without thinking) · 🟡 Noisy / 🔴 Risky (playbook: playbooks/web/13-sql-injection.md)
- [ ] XSS in anything reflected or stored (reviews, names, notes) · 🟡 Noisy (playbook: playbooks/web/09-cross-site-scripting.md)
- [ ] Command injection or SSRF in any "fetch URL", import, or export feature · 🟡 Noisy (playbooks: playbooks/web/12-ssrf.md, playbooks/web/17-xxe-injection.md)
- [ ] File upload: type checks, where files land, and whether they execute · 🟢 Safe / 🔴 Risky (playbook: playbooks/web/21-file-upload.md)
- [ ] API parameters that take a file path: can they return local files? Check whether the call also creates or changes records. · 🔴 Risky (playbook: playbooks/web/02-local-file-read-via-api.md)

## Cloud (if in scope)
- [ ] Public cloud storage hosting an app or files anyone can use. Viewing is fine; submit a form at most once, with fake data. · 🟢 Safe / 🟡 Noisy (playbook: playbooks/web/04-public-cloud-storage-app.md)
- [ ] Cloud roles any user in the account can assume; download one redacted sample at most. · 🟢 Safe (playbook: playbooks/web/05-cloud-role-anyone-can-assume.md)

## Business logic (theme park specific)
- [ ] Ticket price or quantity tampering, negative quantities, coupon reuse · 🔴 Risky (playbooks: playbooks/web/22-business-logic.md, playbooks/general/03-unfamiliar-business-systems.md)
- [ ] Skipping payment steps in a multi-step checkout · 🔴 Risky (playbooks: playbooks/web/22-business-logic.md, playbooks/general/03-unfamiliar-business-systems.md)
- [ ] Fast-pass, queue, or loyalty-point manipulation · 🔴 Risky (playbooks: playbooks/web/22-business-logic.md, playbooks/general/03-unfamiliar-business-systems.md)

## Data sensitivity
- [ ] Card data visible anywhere → PCI DSS context, rate severity accordingly · 🟢 Safe / 🔴 Risky (playbook: playbooks/web/23-card-payment-data.md)
- [ ] Guest PII exposure (names, emails, birthdays, photos) → privacy impact · 🟢 Safe / 🔴 Risky (playbooks: playbooks/web/06-readable-data-in-tokens.md, playbooks/general/01-access-and-identity-data.md)
