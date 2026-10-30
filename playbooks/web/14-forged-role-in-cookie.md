*Draft: command steps not filled in yet.*

# 14. User Role Stored in an Unprotected Cookie

- **Phase:** No credentials (self-registration)
- **Risk:** 🟢 Safe to check: decode our own cookie and see if the role is in it. **Using the forged admin cookie on equipment controls is 🔴 Risky: ask the client contact in writing first, every time.**
- **Tier:** Must know *(proposed)*
- **Finding:** library L16 (`idor-broken-access-control`) *(proposed)*
- **Ports:** 80, 443
- **Tools:** Browser developer tools, Burp Suite, a base64 decoder
- **You need:** a session cookie (in 2024, from a public registration page)

## What it is
The app keeps the user's role inside the cookie, only base64-encoded, with no signature. Change "guest" to "admin" and the server believes it.

**The 2024 example:** the app was a tram controller, and the forged cookie could start and stop the trams. The 2024 team emailed the engagement contact, got written permission, and the tram start/stop became one of their biggest scores. The controller side is in OT #03 (`ot/03-unauthenticated-controllers.md`).

**Lesson:** asking unlocks the big findings. Prove the forged role on a harmless admin page first, then ask in writing before touching anything that moves.

**Fix to recommend:** keep roles on the server (server-side sessions) or use signed tokens such as JWTs that are checked on every request.

## Commands
[[TODO: Copy the steps from the 2024 doc "Web - Tram Controller Authentication Flawed.docx". Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the original cookie, decoded, showing the role.
- `evidence/F-NNN-02.png`: the changed cookie accepted on a harmless admin page.
- The client contact's written permission (the email), before any equipment action.
- `evidence/F-NNN-03.png`: the equipment action and its result, only with that permission.

## Practice
- PortSwigger Web Security Academy, access control and authentication labs *(proposed)*

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
