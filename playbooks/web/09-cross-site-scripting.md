*Draft: command steps not filled in yet.*

# 9. Cross-Site Scripting (XSS)

- **Phase:** No credentials
- **Risk:** 🟡 Noisy: test payloads show up in logs and may trip a web firewall. Test in our own browser only; never send a crafted link to a real user.
- **Tier:** Must know
- **Finding:** none in the library yet
- **Ports:** 80, 443
- **Tools:** Browser, Burp Suite, a web scanner
- **You need:** nothing

## What it is
The site copies part of a request (a URL parameter, a form field, an error message) into its reply without making it safe. Script put there runs in the browser of whoever opens the link, with their session.

Covers two 2024 docs: a basic check (a harmless script in the URL that shows a pop-up), and a stronger proof (a fake "session expired" login box over the real page).

The pop-up is enough proof for the report. Use the fake login only if the client asks to see impact, and only against our own test account.

**Fix to recommend:** encode output for where it lands (HTML, attribute, script); validate input against an allow-list.

## Commands
**Reflected** - Malicious script injected through a request and reflected in the server's response.
`?q=<script>alert(1)</script>` — Payload echoed in response.
**Stored** Malicious script saved on the server and executed when users view affected content.
`<script>alert(1)</script>` — Payload saved in a comment or profile.
**DOM based** Malicious script executed through client-side JavaScript handling untrusted input.
`#<img src=x onerror=alert(1)> — Payload inserted into DOM via unsafe innerHTML.`

See Portswigger XSS Cheat Sheet: `https://portswigger.net/web-security/cross-site-scripting/cheat-sheet`

## Evidence to capture
- `evidence/F-NNN-01.png`: the URL with the test input and the pop-up or the reflected script in the page source.

## Practice
- PortSwigger Web Security Academy, cross-site scripting labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
