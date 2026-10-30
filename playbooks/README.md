# Playbooks

A **playbook** explains one weakness, how to check for it, what evidence to capture, and where to practise. Checklists give the game-day order; each step links to its playbook.

Each playbook has:
- Phase, Risk, Tier and Finding lines
- "What it is"
- Commands: numbered steps, each with an `Expected:` line
- Evidence to capture
- Practice

⚠️ **Drafts:** a file that starts with "*Draft: command steps not filled in yet.*" or "*Draft, needs review.*" still has `[[TODO: ...]]` slots or unchecked steps. None may remain on competition day.

## Risk key

One key for the playbooks, the recon guide and the checklists.

| Risk | Meaning |
|---|---|
| 🟢 Safe | Read-only; no effect on the client's systems. A single login with valid credentials is Safe. |
| 🟡 Noisy | Likely to stand out in logs or alerts: guessed or blank passwords, many requests at once, or files left on a host. |
| 🔴 Risky | Can break or change the client's systems or data. Approval every time. |
| Prohibited | Forbidden by the rules of engagement. Never run. |

**Two labels** (for example 🟢 Safe / 🔴 Risky): the check has the lower rating; the exploit has the higher. The Risk line says which step is which.

## Tiers

- **Must know:** practise hands-on before the event.
- **Recognize:** know what it is and when it applies.
- **Reference:** look it up when needed.

## Windows

| Playbook | Phase | Risk | Finding |
|---|---|---|---|
| [1. Credentials Exposed in LDAP](windows/01-credentials-in-ldap.md) | Initial access | 🟢 Safe / 🟡 Noisy | L01 |
| [2. Default Guest or Administrator Account Without a Password](windows/02-default-guest-admin-no-password.md) | No credentials | 🟡 Noisy | L20 |
| [3. SMBv1 Enabled](windows/03-smbv1-enabled.md) | No credentials | 🟢 Safe | L22 |
| [4. SMB Signing Not Required](windows/04-smb-signing-not-required.md) | No credentials | 🟢 Safe | L03 |
| [5. PrintNightmare](windows/05-printnightmare.md) | No credentials | 🟢 Safe / 🔴 Risky | L22 |
| [6. ZeroLogon](windows/06-zerologon.md) | No credentials | 🟡 Noisy / Prohibited | L22 |
| [7. Kerberos Pre-Authentication Disabled (AS-REP Roasting)](windows/07-asrep-roasting.md) | No credentials | 🟡 Noisy | L05 |
| [8. PetitPotam](windows/08-petitpotam.md) | No credentials | 🟡 Noisy / 🔴 Risky | L03 |
| [9. EternalBlue](windows/09-eternalblue.md) | No credentials | 🟢 Safe / 🔴 Risky | L22 |
| [10. Indicators of Compromise: Hacking Tools Present](windows/10-hacking-tools-present.md) | Low credentials | 🟢 Safe | — |
| [11. Windows Firewall Disabled](windows/11-firewall-disabled.md) | Low credentials | 🟢 Safe | — |
| [12. Windows Real-Time Protection Disabled](windows/12-real-time-protection-disabled.md) | Low credentials | 🟢 Safe | — |
| [13. Sensitive Information in Active Directory Comments](windows/13-secrets-in-ad-comments.md) | Low credentials | 🟢 Safe | L01 |
| [14. Vendor Machines Are Domain-Joined](windows/14-vendors-domain-joined.md) | SYSTEM credentials | 🟢 Safe | — |
| [15. Workstation Accounts Have the Administrator Role](windows/15-workstation-accounts-admin.md) | SYSTEM credentials | 🟢 Safe | L07 |
| [16. Internet Explorer Enabled](windows/16-internet-explorer-enabled.md) | Low credentials | 🟢 Safe | L22 |
| [17. Accounts with Misconfigured Privileges](windows/17-misconfigured-privileges.md) | Low credentials | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L07 |
| [19. Authenticated Users Can Add Workstations to the Domain](windows/19-users-can-add-workstations.md) | SYSTEM credentials | 🟢 Safe / 🔴 Risky | — |
| [20. Shutdown Without Login](windows/20-shutdown-without-login.md) | Low credentials | 🟢 Safe / 🔴 Risky | — |
| [21. Upgrade End-of-Life Systems](windows/21-upgrade-systems.md) | Low credentials | 🟢 Safe | L22 |
| [22. Juicy Potato](windows/22-juicy-potato.md) | Escalation | 🔴 Risky | — |
| [23. NoPac](windows/23-nopac.md) | Escalation | 🟢 Safe / 🔴 Risky | — |
| [25. Kerberoasting](windows/25-kerberoasting.md) | Escalation | 🟡 Noisy | L04 |
| [26. Misconfigured Password Policy](windows/26-password-policy.md) | Low credentials | 🟢 Safe | L06 |

Numbers follow the 2024 run list; #18 and #24 have no playbook.

## Web

| Playbook | Phase | Risk | Finding |
|---|---|---|---|
| [0. OWASP Top 10 (2021): Web Overview](web/00-owasp-top-10.md) | Prep | none | — |
| [1. Unauthenticated Endpoint Exposes Data](web/01-unauthenticated-endpoint.md) | No credentials | 🟢 Safe | L16 |
| [2. API Parameter Reads Local Files](web/02-local-file-read-via-api.md) | No credentials | 🔴 Risky | L16 |
| [3. Deprecated API Endpoint Sends Data to Any Host](web/03-deprecated-api-endpoint.md) | No credentials | 🟢 Safe / 🟡 Noisy | L16 |
| [4. Public Cloud Storage Hosts an App Anyone Can Use](web/04-public-cloud-storage-app.md) | No credentials | 🟢 Safe / 🟡 Noisy | — |
| [5. Cloud Role Any User Can Assume](web/05-cloud-role-anyone-can-assume.md) | Low credentials | 🟢 Safe | L07 |
| [6. Readable Data in Tokens, Responses and Files](web/06-readable-data-in-tokens.md) | No credentials | 🟢 Safe | — |
| [7. Exposed .git Folder](web/07-git-leakage.md) | No credentials | 🟢 Safe / 🟡 Noisy | — |
| [8. HSTS Not Enabled](web/08-hsts-not-enabled.md) | No credentials | 🟢 Safe | L21 |
| [9. Cross-Site Scripting (XSS)](web/09-cross-site-scripting.md) | No credentials | 🟡 Noisy | — |
| [10. Sensitive Cookies Without the HttpOnly Flag](web/10-cookies-without-httponly.md) | No credentials | 🟢 Safe | L17 |
| [11. Sensitive Cookies Without the Secure Flag](web/11-cookies-without-secure.md) | No credentials | 🟢 Safe | L17 |
| [12. Server-Side Request Forgery (SSRF)](web/12-ssrf.md) | No credentials or Low credentials | 🟡 Noisy | — |
| [13. SQL Injection](web/13-sql-injection.md) | No credentials or Low credentials | 🟡 Noisy / 🔴 Risky | L15 |
| [14. User Role Stored in an Unprotected Cookie](web/14-forged-role-in-cookie.md) | No credentials | 🟢 Safe / 🔴 Risky | L16 |
| [15. Username Enumeration via Password Reset](web/15-username-enumeration-password-reset.md) | No credentials | 🟡 Noisy | L17 |
| [16. No Limit on Login Attempts](web/16-excessive-login-attempts.md) | No credentials | 🟡 Noisy / 🔴 Risky | L17 |
| [17. XML External Entity (XXE) Injection](web/17-xxe-injection.md) | No credentials | 🟡 Noisy | — |
| [18. Broken Access Control: IDOR and Horizontal Access](web/18-idor-horizontal-access.md) | Low credentials | 🟢 Safe / 🔴 Risky | L16 |
| [19. Fingerprinting and Known CVEs](web/19-fingerprinting-known-cves.md) | No credentials | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L22 |
| [20. Password Reset Flow Weaknesses](web/20-password-reset-flow.md) | No credentials | 🟡 Noisy / 🔴 Risky | L17 |
| [21. File Upload Weaknesses](web/21-file-upload.md) | No credentials or Low credentials | 🟢 Safe / 🔴 Risky | — |
| [22. Business Logic Flaws](web/22-business-logic.md) | Low credentials | 🟢 Safe / 🔴 Risky | — (related L16) |
| [23. Card and Payment Data Exposure](web/23-card-payment-data.md) | Any | 🟢 Safe / 🔴 Risky | — |

## Linux

Linux services and hosts. Identification commands come from the Recon Field Guide (`playbooks/recon/RECON-GUIDE.md`, Parts 3 and 8). The game-day order is `checklists/15-linux.md`.

| Playbook | Phase | Risk | Finding |
|---|---|---|---|
| [1. Database Without a Password or Using a Default Password](linux/01-default-database-auth.md) | Discovery | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L20 |
| [2. Weak, Default or Reused SSH and Administrator Passwords](linux/02-weak-ssh-admin-passwords.md) | Initial access | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L20 |
| [3. Anonymous FTP and Open NFS Exports](linux/03-anonymous-ftp-open-nfs.md) | Discovery | 🟢 Safe / 🟡 Noisy / 🔴 Risky | — (related L21) |
| [4. SNMP Default Community String](linux/04-snmp-default-community.md) | Discovery | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L02 |
| [5. Secrets in Files and Weak Key Permissions](linux/05-secrets-in-files.md) | Authenticated enumeration | 🟢 Safe / 🔴 Risky | — |
| [6. Linux Privilege Escalation Misconfigurations](linux/06-linux-privilege-escalation.md) | Escalation | 🟢 Safe / 🔴 Risky | L14 |
| [7. Outdated Software with Known Vulnerabilities](linux/07-outdated-linux-software.md) | Discovery | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L22 |

## OT

Industrial control systems: HMIs, controllers and paths to them. Read the OT / ICS Safe-Testing Sheet (`checklists/30-ot-ics-safe.md`) first. ⚠️ **Anything beyond identification needs the client contact's written approval every time.**

| Playbook | Phase | Risk | Finding |
|---|---|---|---|
| [1. HMI Reachable Without a Login](ot/01-unauthenticated-hmi.md) | Discovery | 🟢 Safe / 🔴 Risky / Prohibited | — (related L18) |
| [2. Default Passwords on HMIs or Engineering Software](ot/02-default-hmi-passwords.md) | Discovery | 🟢 Safe / 🔴 Risky / Prohibited | L20 |
| [3. Controllers Accept Commands Without Authentication — Identify Only](ot/03-unauthenticated-controllers.md) | Discovery | 🟢 Safe / 🔴 Risky / Prohibited | L19 |
| [4. OT Reachable from the Office or IT Network](ot/04-it-to-ot-reachability.md) | Discovery | 🟢 Safe / 🔴 Risky / Prohibited | L18 |
| [5. OT Files Stored on Office Shares](ot/05-ot-files-on-shares.md) | Discovery (IT side) | 🟢 Safe / 🔴 Risky / Prohibited | — (related L18) |

## General

Weaknesses that show up on any host, share or web app, not in one lane.

| Playbook | Phase | Risk | Finding |
|---|---|---|---|
| [1. Access and Identity Data: Badges, Barcodes, QR Codes](general/01-access-and-identity-data.md) | Any | 🟢 Safe / 🔴 Risky | — |
| [2. Pivoting and Trust Boundaries](general/02-pivoting-and-trust-boundaries.md) | Movement and trust mapping | 🟢 Safe / 🟡 Noisy / 🔴 Risky | L07 (related L11, L18) |
| [3. Unfamiliar Business Systems](general/03-unfamiliar-business-systems.md) | Discovery and business-impact mapping | 🟢 Safe / 🟡 Noisy / 🔴 Risky / Prohibited | no single entry (L16, L18 or L19 as applicable) |

## AI

Chatbots, assistants and model endpoints. The game-day order is `checklists/60-ai-llm.md`.

| Playbook | Phase | Risk | Finding |
|---|---|---|---|
| [1. Prompt Injection](ai/01-prompt-injection.md) | Application testing | 🟢 Safe / 🟡 Noisy / 🔴 Risky | — |
| [2. Data Leakage Through Chatbots](ai/02-data-leakage-through-chatbots.md) | Application testing | 🟢 Safe / 🟡 Noisy / 🔴 Risky | — (related L16) |

Finding codes point to the findings library (L01–L22). "—" means no library entry yet.
