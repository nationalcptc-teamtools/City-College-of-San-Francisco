*Draft, needs review.*

# 18. Broken Access Control: IDOR and Horizontal Access

- **Phase:** Low credentials (a normal user login)
- **Risk:** 🟢 Safe: changing an ID in a read-only request while logged in as our own test account. 🔴 Risky: creating test accounts, or any request that changes or deletes another user's data. Ask the client contact in writing first, every time, and log it.
- **Tier:** Must know
- **Finding:** library L16 (`idor-broken-access-control`)
- **Ports:** 80, 443
- **Tools:** Burp Suite (proxy and Repeater), a browser
- **You need:** a user login; two test accounts make the proof clean

## What it is
The app shows a record by its ID (`/ticket/1001`, `/api/orders/88`) and checks that you're logged in, but not that the record is yours. Change the ID and you get someone else's ticket, order or profile.

- **IDOR** (insecure direct object reference): the ID in the URL, body or cookie is the only lock.
- **Horizontal access:** user A reaches user B's data at the same privilege level. Vertical access (user to admin) is #14.

**How often:** broken authorization in web apps or APIs appeared in all six recent CPTC environments we reviewed. It's the most common web finding.

⚠️ **Read, don't write.**
- Prove it with a read: one request for one other record.
- Never edit, cancel or delete another user's data to prove the point.

**Fix to recommend:** check on the server, on every request, that the record belongs to the logged-in user. Random IDs alone don't fix it.

**Pattern: browse as yourself, change one ID, stop at the first record that isn't yours.**

**Checklist:** `checklists/20-web-app.md` (Access control: IDOR; Horizontal).

## Commands
1. Browse every feature as a normal user through Burp, intercept off. 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: Burp's history lists every request that carries a record ID.
2. In one read request, change the ID to the next one (`/ticket/1001` → `1002`) and send it once. 🟢 [[NOTE: from checklist 20]]
   Expected: an access-denied error (no finding), or another user's record (finding).
3. [[TODO: Add the two-test-account check (log in as A, request B's record by ID). Creating the accounts is 🔴 Risky: ask the client contact in writing first, every time, log it, and record the accounts in `created-accounts-and-artifacts.csv`.]]
   Expected: B's record shown to A = finding, with clean evidence that names no real customer.
4. [[TODO: Add any write-path check (changing or deleting by ID) only with written approval; 🔴 Risky. No real customer data may be changed.]]
   Expected: Only if approved.

## Evidence to capture
- `evidence/F-NNN-01.png`: the request with the changed ID, and the response showing a record that isn't ours, personal data redacted.
- The logged-in account and the record owner (test account names, or "a real customer", redacted).
- How many IDs could be reached (a range, not a dump).

## Practice
- PortSwigger Web Security Academy, access control labs (IDOR and horizontal privilege escalation).

---
*Written by the CCSF 2026 team from past-CPTC environment research.*
