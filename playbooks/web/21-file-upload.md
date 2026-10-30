*Draft, needs review.*

# 21. File Upload Weaknesses

- **Phase:** No credentials or Low credentials (wherever the upload form is)
- **Risk:** 🟢 Safe: finding upload forms and reading what they say they accept. 🔴 Risky: any upload. It writes a file to the client's server. Ask the client contact in writing first, every time, and log it.
- **Tier:** Must know *(proposed)*
- **Finding:** none in the library yet
- **Ports:** 80, 443
- **Tools:** Burp Suite, a browser
- **You need:** the upload form or endpoint (from browsing or content discovery)

## What it is
An upload form that doesn't check what it receives can take a script instead of a picture. If the server stores it where the web server runs it, that's code execution on the server.

What to look at:
- **Type checks:** only the file extension, or only the browser-supplied `Content-Type`.
- **Where files land:** inside the web root, under a guessable name.
- **Whether they execute:** a stored file that the server runs, not just serves.

**How often:** unrestricted or unauthenticated uploads appeared in four of the six recent CPTC environments we reviewed, several leading to code execution.

⚠️ **Every upload is 🔴 Risky.**
- Get written approval first, then upload a harmless file (plain text, no code).
- Log the file name and path, and remove it afterwards.

**Fix to recommend:** allow-list file types by content, store uploads outside the web root under random names, and never execute them.

**Pattern: find the form, read the rules, ask before the first upload.**

**Checklist:** `checklists/20-web-app.md` (Injection: File upload).

## Commands
1. Browse every feature as a normal user through Burp, intercept off; note each upload form. 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: a list of upload forms and the endpoints they post to.
2. Read what each form says it accepts (page text, the `accept` attribute, client-side checks). 🟢
   Expected: the file types and sizes the app claims to allow.
3. [[TODO: Add the approved harmless-upload check (one plain-text file, logged in `created-accounts-and-artifacts.csv`, removed afterwards). 🔴 Risky: ask the client contact in writing first, every time, and log it. No executable payloads.]]
   Expected: where the file lands and whether the server serves it as-is; nothing executes.

## Evidence to capture
- `evidence/F-NNN-01.png`: the upload form and what it claims to accept.
- If approved: the upload request, the stored path and the response when the file is fetched.
- The written approval, the file name and proof it was removed.

## Practice
- PortSwigger Web Security Academy, file upload vulnerabilities labs.

---
*Written by the CCSF 2026 team from past-CPTC environment research.*
