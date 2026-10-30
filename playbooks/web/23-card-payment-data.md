*Draft, needs review.*

# 23. Card and Payment Data Exposure

- **Phase:** Any: shows up in web pages, APIs, databases and files
- **Risk:** 🟢 Safe: noting where card data is visible, with a redacted sample. 🔴 Risky: copying card data in bulk, or using a payment API or admin function. Ask the client contact in writing first, every time, and log it.
- **Tier:** Recognize
- **Finding:** none in the library yet
- **Ports:** 80, 443; database ports if the data sits there (Linux #01)
- **Tools:** Burp Suite, a browser
- **You need:** wherever the data shows up: a page, an API reply, a database or a file

## What it is
Card numbers, expiry dates and security codes stored or shown where they shouldn't be. PCI DSS, the card industry's standard, says full card numbers must be unreadable when stored and the security code must never be stored after payment.

Where it turns up:
- API replies with full card numbers the page then masks (see #06).
- Unencrypted card columns in a database.
- Exposed payment API documentation, or a payment API that needs no login.
- Logs, exports and backups.

**How often:** card or payment-system findings appeared in about three of the six recent CPTC environments we reviewed: unencrypted card data, exposed or unauthenticated payment APIs.

⚠️ **Prove it with one masked record.**
- Never copy, export or screenshot a full card number.
- Count the records; don't collect them.

**Fix to recommend:** don't store card data you don't need; encrypt or tokenize what you keep; never store the security code; lock down payment APIs.

**Pattern: find it, mask it, count it, stop.**

**Checklist:** `checklists/20-web-app.md` (Data sensitivity: Card data).

## Commands
1. Browse every feature as a normal user through Burp, intercept off; search the history for card-like numbers. 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: any response that carries card data, and where.
2. [[TODO: Add a read-only check for card data in places other playbooks reach (databases via Linux #01, files via Linux #05 or General #1), only after its command and rating are in the Recon Field Guide. Bulk export is 🔴 Risky: ask the client contact in writing first, every time, and log it.]]
   Expected: the location and record count, with one masked sample.

## Evidence to capture
- `evidence/F-NNN-01.png`: where the data shows up, card numbers masked to the last 4 digits.
- The record count and the fields exposed (number, expiry, security code, name).
- Never a full card number, in evidence or in the report.

## Practice
- [[TODO: Pick a practice app with fake card data (test card numbers only) to rehearse masking and counting.]]

---
*Written by the CCSF 2026 team from past-CPTC environment research.*
