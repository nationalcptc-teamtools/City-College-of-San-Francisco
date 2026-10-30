*Draft, needs review.*

# 1. HMI Reachable Without a Login

- **Phase:** Discovery (no credentials needed)
- **Risk:** 🟢 Safe / 🔴 Risky / Prohibited: slow, specific-port identification is Safe; opening an HMI session or logging in is Risky—**ask the client contact in writing first, every time**; anything that could stop or damage a process without permission is Prohibited
- **Tier:** Must know *(proposed)*
- **Finding:** none in the library yet; related library L18 (`ot-network-segmentation`) when the HMI crosses an IT/OT boundary
- **Runs on:** web HMIs, VNC-exposed control screens, operator stations and engineering workstations
- **Ports:** site-specific web ports; 5900 and related VNC ports; identify from scope and approved discovery
- **Tools:** nmap; browser or VNC viewer only after written approval

## What it is
An HMI is the screen operators use to see alarms, measurements and equipment state. If its web page or remote desktop needs no login, anyone who can reach it may get visibility and possibly control.

Past CPTC environments included a dam control screen visible through unauthenticated VNC, and a manufacturing HMI connected to a conveyor controller. The reports disagreed on whether one VNC session was read-only or administrative, which is why the safe proof is exposure and visibility, not a state change.

Follow the Identify steps in the OT / ICS Safe-Testing Sheet (`checklists/30-ot-ics-safe.md`). Don't assume a screen is harmless because it looks read-only.

## Commands

For every broad scan of a range that might contain OT, use the checklist's brittle-port exclusion exactly:

```text
--exclude-ports T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

1. Start from IT-side hostnames, DNS, directory objects, shares and scope notes. Record the suspected HMI host without contacting it directly.
   Expected: A hostname or address plus the source that identified it.
2. If scanning is allowed, use a TCP connect scan against only the expected web or VNC port, slowly: `nmap -sT -Pn -p <HMI_WEB_PORT>,5900 --max-rate 10 <host>`.
   Expected: The expected HMI web or VNC port is open, closed or filtered; no controller commands are sent.
3. Stop before opening a web or VNC session. Opening a session or logging in is 🔴 Risky: **ask the client contact in writing first, every time**.
   Expected: Written approval defines the exact host, method and stopping point.
4. [[TODO: Add a product-specific, read-only confirmation procedure approved for the event; it must not click controls, acknowledge alarms, change values or leave files.]]
   Expected: A screenshot showing access without a login prompt and no evidence of a state change.

## Evidence to capture
- `evidence/F-NNN-01.png`: the approved screen showing the HMI without a login prompt; include the URL or session target and redact operationally sensitive values if required.
- `evidence/F-NNN-02.txt`: the specific-port scan output and timestamp.
- The written approval, ticket or message that authorized opening the session.
- Record the source network so this can be linked to library L18 (`ot-network-segmentation`) when applicable.

## Practice
- [[TODO: Choose an isolated HMI simulator and verify that the confirmation procedure is genuinely read-only before team practice.]]
- Rehearse stopping after proof of exposure and writing impact in operational and safety terms.

---
*Written by the CCSF 2026 team from the OT/ICS safe-testing checklist and past-CPTC environment research.*
