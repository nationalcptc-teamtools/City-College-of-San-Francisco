*Draft: command steps not filled in yet.*

# 11. Sensitive Cookies Without the Secure Flag

- **Phase:** No credentials
- **Risk:** 🟢 Safe *(proposed)*: reading response headers.
- **Tier:** Recognize *(proposed)*
- **Finding:** library L17 (`web-authentication-weakness`) *(proposed)*
- **Ports:** 80, 443
- **Tools:** Browser developer tools, Burp Suite
- **You need:** nothing; a login shows more cookies

## What it is
A cookie without the `Secure` flag can be sent over unencrypted HTTP, where anyone on the network path can read it.

Report it for session cookies and cookies holding user data.

**Fix to recommend:** add `Secure` to the `Set-Cookie` header of every such cookie.

## Commands
[[TODO: Copy the steps from the 2024 doc "Web - Sensitive Cookies Without Secure Flag.docx". Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the `Set-Cookie` header missing the flag, cookie value redacted.

## Practice
- Any site the team runs with a login; check its cookies *(proposed)*

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
