*Draft, needs review.*

# 3. Unfamiliar Business Systems

- **Phase:** Discovery and business-impact mapping
- **Risk:** 🟢 Safe to identify and browse read-only features. Slow OT identification is 🟡 Noisy. Any action that changes a ticket, payment, lock, kiosk, ride, tram or process is 🔴 Risky: ask the client contact in writing first, every time, and log it. An action outside the rules or without required approval is Prohibited.
- **Tier:** Must know *(proposed)*
- **Finding:** no single library entry; use L16 (`idor-broken-access-control`), L18 (`ot-network-segmentation`) or L19 (`unauthenticated-industrial-protocol`) when the root cause fits
- **Ports:** 80, 443 and any discovered application or control-system port
- **Tools:** Browser developer tools, Burp Suite, httpx-toolkit
- **You need:** the rules of engagement and a normal test account when the system requires one

## What it is
An unfamiliar business system is the software that runs the client's actual work: a kiosk, ticketing flow, door lock, payment service, ride control or tram screen. It may look like an ordinary website while holding far more power.

High-impact custom business systems appeared in **all six reviewed CPTC environments**. Examples included banking and cash machines, a dam control screen in a utilities scenario, production conveyors, hotel kiosks and locks, airport tram and baggage systems, and a social-media chatbot. The technology changed. The useful question did not: **what can this system see or change for the business?**

Map the normal workflow before testing unusual behavior. If a button can move equipment, unlock a door, charge money or alter a live record, stop before pressing it.

**Checklists:** Web / Patron Systems: Map it (`checklists/20-web-app.md`), Web / Patron Systems: Business logic (`checklists/20-web-app.md`), and OT / ICS: Before touching anything (`checklists/30-ot-ics-safe.md`).

## Commands

1. Identify a web service without logging in: `httpx-toolkit -u http://<host>:<port> -title -tech-detect` 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: The title and technology give the system a name. They do not tell us its business effect.
2. In Burp, browse every feature as a normal user and make a one-line map of **input → decision → business result**. Use read-only pages and our own test records only. 🟢 Safe. [[NOTE: from checklist 20]]
   Expected: A short workflow map shows identities, objects, roles, approval steps and actions with real-world effects.
3. If the system might control physical equipment, stop normal web testing and identify it through the OT checklist. Confirm scope and tell the team before traffic to suspected OT ranges. 🟡 Noisy. [[NOTE: from checklist 30]]
   Expected: The team knows the suspected system, its address and why it may be safety-critical. No control action has been sent.
4. [[TODO: Write a system-specific test for tickets, payments, locks, kiosks, rides or trams. Any write or process action is 🔴 Risky: ask the client contact in writing first, every time, and log it. Do not include an exploit command.]]
   Expected: The approved test names one harmless record or action, the stop condition and how the team will verify recovery.

## Evidence to capture

- `evidence/F-NNN-01.png`: the system title or landing page, without customer data.
- `evidence/F-NNN-02.png`: the normal user's read-only workflow or role boundary.
- The input → decision → business result map.
- The written approval and log entry before any action that changes data or a physical process.

## Practice

- **Free, public and legal:** [PortSwigger Web Security Academy: Business logic vulnerabilities](https://portswigger.net/web-security/logic-flaws). Use the Academy labs, not a live business system.

---
*Study draft for the CCSF 2026 team.*
