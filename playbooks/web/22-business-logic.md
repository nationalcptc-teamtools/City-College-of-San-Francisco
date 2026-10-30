*Draft, needs review.*

# 22. Business Logic Flaws

- **Phase:** Low credentials (a normal user login)
- **Risk:** 🟢 Safe: browsing a flow and reading the requests. 🔴 Risky: submitting a changed price, quantity, coupon or order. It creates or changes client records. Ask the client contact in writing first, every time, and log it.
- **Tier:** Must know *(proposed)*
- **Finding:** none in the library yet; library L16 (`idor-broken-access-control`) when the flaw is a missing permission check
- **Ports:** 80, 443
- **Tools:** Burp Suite (proxy and Repeater), a browser
- **You need:** a test account; written approval before the first changed request

## What it is
The code works as written, but the rules it enforces are wrong. Scanners don't find these; you find them by thinking like the business.

- **Prices and quantities:** the price comes from the browser; negative or huge quantities are accepted.
- **Coupons and points:** a code works twice; points can be moved or created.
- **Skipped steps:** jump from cart to confirmation without paying; skip a check in a multi-step flow.
- **Industry flows:** the custom system's own rules (tickets, queues, bookings, transfers).

**How often:** business-logic or workflow flaws appeared in about four of the six recent CPTC environments we reviewed, usually in the client's custom systems (money transfers, loyalty, payment devices). Those systems have the biggest business impact.

⚠️ **Watch, then ask.**
- Map the flow and spot the suspect value without changing anything.
- Every changed submission creates a real record: approval first, test account only.

**Fix to recommend:** enforce every business rule on the server (price, quantity, step order, one-time use), never in the browser.

**Pattern: map the flow, spot the value the server trusts, ask, then change one thing.**

**Checklist:** `checklists/20-web-app.md` (Business logic).

## Commands
1. Browse the whole flow as a normal user through Burp, intercept off. 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: every step's request in Burp's history, with the values the browser sends (price, quantity, step, coupon).
2. List which values come from the browser and which the server should own. 🟢
   Expected: candidate values to test, with the step each appears in.
3. [[TODO: Add the approved single-change test (one changed value, one submission, test account only, the record logged and cancelled or reverted). 🔴 Risky: ask the client contact in writing first, every time, and log it.]]
   Expected: the server rejects the change (no finding), or accepts it (finding).

## Evidence to capture
- `evidence/F-NNN-01.png`: the original request and the changed one, side by side.
- `evidence/F-NNN-02.png`: the result (wrong total, order placed, step skipped).
- The written approval, the record created and how it was reverted.

## Practice
- PortSwigger Web Security Academy, business logic vulnerabilities labs.

---
*Written by the CCSF 2026 team from past-CPTC environment research.*
