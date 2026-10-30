*Draft: command steps not filled in yet.*

# 2. API Parameter Reads Local Files

- **Phase:** No credentials
- **Risk:** 🔴 Risky: in 2024 the vulnerable call also **created a database record** each time it ran, so every test changed client data. Approval every time. Reading a file through an endpoint that changes nothing would be 🟡 Noisy.
- **Tier:** Must know
- **Finding:** library L16 (`idor-broken-access-control`)
- **Ports:** 80, 443
- **Tools:** Burp Suite, a base64 decoder
- **You need:** the endpoint and its parameters (from content discovery)

## What it is
An API takes a file path as a parameter (in 2024, a profile picture's path) and returns the file's contents, here base64-encoded. Anyone who can call it can read system files such as the password and password-hash files, or download the application itself.

In 2024 this was the first step of a chain: the downloaded app listed its own routes, which led to #01 and #03.

**Fix to recommend:** don't accept file paths from users; if pictures are needed, use restricted uploads. Require a login.

## Commands
- **Prev. Example:** Baggage Check-In App Allows Unauthenticated Reading of System Files

- **Methodology:** brute-force enumeration leads to web API, unauthenticated GET endpoint `/api/v3/endpoint/add` that adds a entry in the db and returns a response.

Response with the contents of those files encoded in base64 returned as the value associated with the Picture JSON key.

Obtain passwords from `/etc/passwd` base64 blob.
Extract hashes from `/etc/shadow`.

-**Unauthenticated endpoints:**  Look for endpoints like `/api/v2/print/send` that allow you to do some action - ie send GET query parameters to a remote system with a simple URL.

**Testing:** Run a TCP listener somewhere like a jump box and call each of these API endpoints.

## Evidence to capture
- `evidence/F-NNN-01.png`: the request with the path parameter and the response.
- `evidence/F-NNN-02.png`: the decoded file, hashes redacted to the first and last characters.

## Practice
- PortSwigger Web Security Academy, path traversal labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
