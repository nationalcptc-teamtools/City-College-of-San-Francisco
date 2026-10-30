*Draft, needs review.*

# 3. Controllers Accept Commands Without Authentication — Identify Only

- **Phase:** Discovery (no credentials needed)
- **Risk:** 🟢 Safe / 🔴 Risky / Prohibited: slow port identification is Safe; any direct protocol request, controller command or value change is Risky—**ask the client contact in writing first, every time**; anything that could stop or damage a process without permission is Prohibited
- **Tier:** Must know
- **Finding:** library L19 (`unauthenticated-industrial-protocol`)
- **Runs on:** PLCs, RTUs, building controllers, safety-adjacent controllers and protocol gateways
- **Ports:** 502 Modbus/TCP; 102 S7comm; 44818/TCP and 2222/UDP EtherNet/IP; other ports listed in the safe-testing sheet
- **Tools:** nmap, limited to the checklist's approved TCP-connect and read-only identification steps

## What it is
Many industrial protocols were designed for trusted, isolated networks. A controller may accept a valid message from any reachable computer because the protocol has no login, signing or per-user authorization.

Past CPTC environments included simulated power and dam controllers reachable through Modbus and a manufacturing controller linked to a conveyor HMI. Reports showed unauthenticated reachability and read access; writes would have carried much greater operational and safety consequences.

This playbook is **identify only**. An open industrial port and, where expressly allowed, one read-only identification request are enough for escalation and reporting. Use library L19 (`unauthenticated-industrial-protocol`) and the OT / ICS Safe-Testing Sheet (`checklists/30-ot-ics-safe.md`).

**The 2024 example:** a forged cookie could start and stop trams. The 2024 team emailed the engagement contact, got written permission, and the tram start/stop became one of their biggest scores. How they got in is in Web #14 (`web/14-forged-role-in-cookie.md`).

**Lesson:** asking unlocks the big findings, but it doesn't make the action safe. Ask in writing before touching anything that moves.

## Commands

For every broad scan of a range that might contain OT, use the checklist's brittle-port exclusion exactly:

```text
--exclude-ports T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

1. Identify suspected controller addresses from scope, hostnames, DNS, directory objects, shares, HMI project material and vendor documentation before sending direct traffic.
   Expected: A candidate host, protocol and business role supported by existing evidence.
2. If scanning is allowed, check only the recognized TCP ports, slowly and one host at a time: `nmap -sT -Pn -p 502,102,44818 --max-rate 10 <host>`.
   Expected: One or more recognized industrial ports are open, closed or filtered.
3. Only after written approval for this host and request, identify Modbus on one host: `nmap -sT -p 502 --script modbus-discover <host>`. This direct protocol request is 🔴 Risky: **ask the client contact in writing first, every time**.
   Expected: Read-only device information is returned without authentication; no coil, register, setpoint or mode is changed.
4. Stop after identification. Do not send a write, start, stop, reset, upload, download or mode-change request. Sending any controller command is 🔴 Risky: **ask the client contact in writing first, every time**.
   Expected: Evidence of exposure only.
5. [[TODO: Add protocol-specific read-only identification for any non-Modbus device, after verifying it against the event ROE and the actual product; no generic write-capable client command belongs here.]]
   Expected: Product-specific identification with no state change.

## Evidence to capture
- `evidence/F-NNN-01.txt`: the slow specific-port result.
- `evidence/F-NNN-02.txt`: approved read-only identification output, if performed.
- The source network, destination, timestamp and written approval for any direct protocol interaction.
- Record no claim that writes work unless the client separately authorized and observed that test.

## Practice
- [[TODO: Choose an isolated controller simulator and confirm that every retained identification step is read-only.]]
- Practise writing the library L19 (`unauthenticated-industrial-protocol`) finding from port and read-only evidence alone.

---
*Written by the CCSF 2026 team from the OT/ICS safe-testing checklist and past-CPTC environment research.*
