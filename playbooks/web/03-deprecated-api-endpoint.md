*Draft: command steps not filled in yet.*

# 3. Deprecated API Endpoint Sends Data to Any Host

- **Phase:** No credentials
- **Risk:** 🟡 Noisy: the call makes the client's server connect out to our jump host and triggers an app action (in 2024, a print job). Any login with credentials it leaks is one valid login: 🟢 Safe under the login rule, but pass them to the team first.
- **Tier:** Recognize
- **Finding:** library L16 (`idor-broken-access-control`)
- **Ports:** 80, 443
- **Tools:** Burp Suite, a listener on the jump host
- **You need:** the route list (see #01); a listener on **our jump host only**

## What it is
Old API versions often keep running after a new one replaces them, without the new checks. In 2024 an old, unauthenticated endpoint let the caller choose where the app sent its data. Pointed at our listener, it sent customer data and the database and system passwords.

**Fix to recommend:** turn off deprecated routes; send data only to known, authenticated systems over encrypted channels.

## Commands
[[TODO: Copy the steps from the 2024 doc "API - Deprecated API Endpoints.docx" (its first finding). Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the request naming our listener as the destination.
- `evidence/F-NNN-02.png`: what the listener received, secrets and personal data redacted.

## Practice
- PortSwigger Web Security Academy, SSRF labs; the idea is the same, with the client's server connecting out

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
