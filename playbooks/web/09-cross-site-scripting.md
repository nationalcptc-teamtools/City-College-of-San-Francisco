*Draft: command steps not filled in yet.*

# 9. Cross-Site Scripting (XSS)

- **Phase:** No credentials
- **Risk:** 🟡 Noisy *(proposed)*: test payloads show up in logs and may trip a web firewall. Test in our own browser only; never send a crafted link to a real user.
- **Tier:** Must know *(proposed)*
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
[[TODO: Copy the steps from the 2024 doc "Web - Reflected XSS.docx" and "Web - XSS.docx". Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the URL with the test input and the pop-up or the reflected script in the page source.

## Practice
- PortSwigger Web Security Academy, cross-site scripting labs *(proposed)*

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
