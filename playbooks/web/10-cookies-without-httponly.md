*Draft: command steps not filled in yet.*

# 10. Sensitive Cookies Without the HttpOnly Flag

- **Phase:** No credentials
- **Risk:** 🟢 Safe: reading response headers.
- **Tier:** Recognize
- **Finding:** library L17 (`web-authentication-weakness`)
- **Ports:** 80, 443
- **Tools:** Browser developer tools, Burp Suite
- **You need:** nothing; a login shows more cookies

## What it is
A cookie without the `HttpOnly` flag can be read by scripts in the page. With XSS (#09), an attacker can steal a user's session cookie.

Report it for session cookies; other cookies matter less.

**Fix to recommend:** add `HttpOnly` to the `Set-Cookie` header of every session cookie.

## Commands
- **Cookies without the HTTPOnly flag set** are more vulnerable to XSS attacks

## Evidence to capture
- `evidence/F-NNN-01.png`: the `Set-Cookie` header missing the flag, cookie value redacted.

## Practice
- Any site the team runs with a login; check its cookies

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
