*Draft, needs review.*

# 2. Default Passwords on HMIs or Engineering Software

- **Phase:** Discovery (identification first; credentials only with approval)
- **Risk:** 🟢 Safe / 🔴 Risky / Prohibited: identifying the product is Safe; attempting a password or logging in to an HMI is Risky—**ask the client contact in writing first, every time**; brute force or any action that could stop or damage a process without permission is Prohibited
- **Tier:** Must know *(proposed)*
- **Finding:** library L20 (`default-credentials`); related library L18 (`ot-network-segmentation`) when reachable from IT
- **Runs on:** HMI servers, operator stations, engineering workstations and vendor engineering suites
- **Ports:** product-specific web, VNC and engineering-service ports
- **Tools:** nmap for slow port identification; approved vendor documentation; no password-spraying tools

## What it is
HMIs and engineering packages are often installed with vendor or integrator credentials. If they are never changed, anyone who can reach the service gets an operator's or engineer's access.

Past CPTC environments included default credentials on a manufacturing HMI and weak stored administrator credentials on a utilities control screen. The danger in both was what the software connected to: operational displays and controllers, not just another server.

Identifying the product and documenting its published default is useful evidence. Testing that password on an HMI is 🔴 Risky because even a successful login may create a session or expose active controls. Follow the OT / ICS Safe-Testing Sheet (`checklists/30-ot-ics-safe.md`).

## Commands

For every broad scan of a range that might contain OT, use the checklist's brittle-port exclusion exactly:

```text
--exclude-ports T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

1. Identify suspected HMI or engineering hosts from IT-side hostnames, DNS, directory objects, shares, vendor manuals and scope notes.
   Expected: A product or host candidate supported by a recorded source.
2. If scanning is allowed, check only the expected port with a slow TCP connect scan: `nmap -sT -Pn -p <APPROVED_PORT> --max-rate 10 <host>`.
   Expected: The expected service is open, closed or filtered without an authentication attempt.
3. Record the exact product and version only from already available documentation or a safely exposed banner. Do not run a version-intensity sweep.
   Expected: Enough product detail for a human to check the vendor's official default-credential documentation.
4. Stop before trying any credential. A login to an HMI is 🔴 Risky: **ask the client contact in writing first, every time**. Never brute force an HMI.
   Expected: Written approval states one credential, one target, one attempt and the required stopping point.
5. [[TODO: Insert the official vendor source and a one-attempt, client-approved validation procedure; include an immediate logout and no-control-interaction rule.]]
   Expected: Either one successful login with no state change or a failed attempt followed by an immediate stop.

## Evidence to capture
- `evidence/F-NNN-01.png`: product/version evidence and the official vendor source for the default credential.
- If approved, `evidence/F-NNN-02.png`: the first post-login screen, captured without clicking or changing anything.
- The exact written approval and the time of the single validation attempt.
- Link the finding to library L18 (`ot-network-segmentation`) if an ordinary IT position could reach the service.

## Practice
- [[TODO: Select an isolated vendor simulator or training image and document its safe login/logout procedure.]]
- Practise distinguishing product identification from credential validation; only the latter proves the default still works.

---
*Written by the CCSF 2026 team from the OT/ICS safe-testing checklist and past-CPTC environment research.*
