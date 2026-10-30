*Draft: command steps not filled in yet.*

# 6. Readable Data in Tokens, Responses and Files

- **Phase:** No credentials; more shows up after a login
- **Risk:** 🟢 Safe: decoding and reading what the app already sends us.
- **Tier:** Must know
- **Finding:** none in the library yet
- **Ports:** 80, 443
- **Tools:** Burp Suite, browser developer tools, a base64 decoder, a JWT decoder, exiftool (file metadata)
- **You need:** traffic from normal use of the app (Burp history); any photos or PDFs the site publishes

## What it is
Apps often hand out data that looks hidden but anyone can read. Check four places:

1. **Base64 values** in cookies, hidden form fields and URL parameters. Decoding needs no key. Look for names, IDs, roles (see #14) or passwords.
2. **JWT payloads.** A JSON Web Token's middle part is base64 too, so anyone holding it can read the user, role, email and expiry. The signature stops changes, not reading.
3. **APIs that return more fields than the page shows.** The page shows a name; the reply also carries the address, ID number or password hash. OWASP calls this excessive data exposure (API Security Top 10, 2019; in the 2023 list it's part of API3).
4. **Metadata in published photos and PDFs:** author names, usernames, software versions, internal paths, GPS location.

Each item alone is often low severity. Usernames and internal paths feed other attacks (password guessing, #15, #16); personal data raises it.

Barcodes, QR codes and badge data are in the General playbook `general/01-access-and-identity-data.md`.

**Fix to recommend:** keep sensitive data on the server; return only the fields the page needs; strip metadata before publishing files.

## Commands
[[TODO: Write the steps; no 2024 doc covers these four checks. One step per place above: decode a base64 value, decode a JWT, compare an API reply with what the page shows, read one published file's metadata. Use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the encoded value and its decoded form, side by side, personal data redacted.
- `evidence/F-NNN-02.png`: for an API, the reply's extra fields next to the page that hides them.
- For metadata: the file name and the fields found.

## Practice
- PortSwigger Web Security Academy, JWT and information disclosure labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
