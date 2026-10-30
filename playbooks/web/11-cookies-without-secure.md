*Draft: command steps not filled in yet.*

# 11. Sensitive Cookies Without the Secure Flag

- **Phase:** No credentials
- **Risk:** 🟢 Safe: reading response headers.
- **Tier:** Recognize
- **Finding:** library L17 (`web-authentication-weakness`)
- **Ports:** 80, 443
- **Tools:** Browser developer tools, Burp Suite
- **You need:** nothing; a login shows more cookies

## What it is
A cookie without the `Secure` flag can be sent over unencrypted HTTP, where anyone on the network path can read it.

Report it for session cookies and cookies holding user data.

**Fix to recommend:** add `Secure` to the `Set-Cookie` header of every such cookie.

## Commands
- **Cookies without a secure flag set** are more vulnerable to XSS attacks
Without the secure flag set, cookie data can be transmitted over plaintext.

## Evidence to capture
- `evidence/F-NNN-01.png`: the `Set-Cookie` header missing the flag, cookie value redacted.

## Practice
- Any site the team runs with a login; check its cookies

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
