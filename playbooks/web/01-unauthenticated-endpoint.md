*Draft: command steps not filled in yet.*

# 1. Unauthenticated Endpoint Exposes Data

- **Phase:** No credentials (content discovery)
- **Risk:** 🟢 Safe *(proposed)*: loading a page. Capture a few redacted rows, never the whole data set.
- **Tier:** Must know *(proposed)*
- **Finding:** library L16 (`idor-broken-access-control`) *(proposed)*
- **Ports:** 80, 443
- **Tools:** Browser, Burp Suite, a content-discovery tool (gobuster or similar)
- **You need:** nothing; a list of routes helps (from content discovery, or from the app itself)

## What it is
A route that should need a login, or should never have shipped (a developer or debug page), answers anyone. In 2024 one returned a full dump of the customer database, personal data included.

Where routes come from: content discovery, JavaScript files, API docs, or the route list an app prints when it starts in debug mode (2024 got it this way after downloading the app through #02).

**Fix to recommend:** remove development routes from production, and require a login on every route that returns data.

## Commands
[[TODO: Copy the steps from the 2024 doc "Web - Unauthenticated Endpoint.docx". Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the route in the address bar and the response, personal data redacted.
- A count of the records exposed (for the business impact), not the records themselves.

## Practice
- PortSwigger Web Security Academy, access control labs *(proposed)*

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
