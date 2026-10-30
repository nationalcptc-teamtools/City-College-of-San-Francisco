*Draft: command steps not filled in yet.*

# 2. API Parameter Reads Local Files

- **Phase:** No credentials
- **Risk:** 🔴 Risky: in 2024 the vulnerable call also **created a database record** each time it ran, so every test changed client data. Approval every time. Reading a file through an endpoint that changes nothing would be 🟡 Noisy.
- **Tier:** Must know *(proposed)*
- **Finding:** library L16 (`idor-broken-access-control`) *(proposed)*
- **Ports:** 80, 443
- **Tools:** Burp Suite, a base64 decoder
- **You need:** the endpoint and its parameters (from content discovery)

## What it is
An API takes a file path as a parameter (in 2024, a profile picture's path) and returns the file's contents, here base64-encoded. Anyone who can call it can read system files such as the password and password-hash files, or download the application itself.

In 2024 this was the first step of a chain: the downloaded app listed its own routes, which led to #01 and #03.

**Fix to recommend:** don't accept file paths from users; if pictures are needed, use restricted uploads. Require a login.

## Commands
[[TODO: Copy the steps from the 2024 doc "API - Deprecated API Endpoints.docx" (its second finding, "Allows Unauthenticated Reading of System Files"). Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the request with the path parameter and the response.
- `evidence/F-NNN-02.png`: the decoded file, hashes redacted to the first and last characters.

## Practice
- PortSwigger Web Security Academy, path traversal labs *(proposed)*

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
