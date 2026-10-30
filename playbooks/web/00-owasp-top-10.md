# 0. OWASP Top 10 (2021): Web Overview

- **Phase:** Prep (study before the event; skim on game day to see what to look for)
- **Risk:** none: a reading list, no commands
- **Tier:** Reference *(proposed)*

## What it is
The OWASP Top 10 is the standard list of common web-app weaknesses. The 2024 overview doc lists each category, what it looks like and the tools that find it. This page maps each to our Web playbooks.

| OWASP 2021 category | What to look for | Our playbooks |
|---|---|---|
| A01 Broken Access Control | pages or API calls that work without the right login or role; changing an ID shows someone else's data | #01, #02, #04, #05, #14, #18, #22 |
| A02 Cryptographic Failures | data sent unencrypted, weak or missing encryption, missing security headers | #06, #08, #11, #23 |
| A03 Injection (XSS included) | input that reaches a database, the page or a command unchanged | #09, #13 |
| A04 Insecure Design | flaws in how a feature was planned, not in its code | #03, #14, #21, #22 |
| A05 Security Misconfiguration (XXE included) | default settings, debug pages, verbose errors, files left in place | #07, #10, #17 |
| A06 Vulnerable and Outdated Components | old versions of the app, its libraries or the server | #19; Windows #21 (same idea) |
| A07 Identification and Authentication Failures | unlimited login attempts, user lists, weak session handling | #15, #16, #20 |
| A08 Software and Data Integrity Failures | updates or data the app trusts without checking | none yet |
| A09 Security Logging and Monitoring Failures | our tests trigger no alerts | none (a report observation) |
| A10 Server-Side Request Forgery | the server fetches a URL we choose | #03, #12 |

**Tools the 2024 doc names:** Burp Suite, ZAP, Postman, sqlmap, Nikto, Nessus/OpenVAS, gobuster, SSRFmap, Metasploit. Check each against our tool list before relying on it.

**Not carried over:** the doc's incidence and exploit-weight numbers per category (they're on the OWASP site).

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
