*Draft: command steps not filled in yet.*

# 5. PrintNightmare

- **Phase:** No credentials (scan only)
- **Risk:** 🟢 Safe to check. **Exploiting is 🔴 Risky: scan only, do not exploit**.
- **Tier:** Must know, at check level only
- **Finding:** library L22 (`outdated-software`)
- **Runs on:** Windows 7, 8.1, 10; Server 2008 through 2022, when unpatched
- **Ports:** 445 (SMB, which carries the Print Spooler's RPC calls)
- **Tools:** impacket-rpcdump (Impacket), egrep

## What it is
PrintNightmare (CVE-2021-34527) is a bug in the Windows Print Spooler service. An unpatched host running the spooler lets a low-privileged user run code as SYSTEM, the highest local privilege.

**Why scan only:** exploiting it loads code into a core Windows service and can crash the spooler or leave files on a client's server. Reporting the exposed, unpatched service is enough.

The check is whether the spooler's remote interface is reachable; pair it with the host's patch level.

## Commands
1. `impacket-rpcdump <TARGET_IP> | egrep 'MS-RPRN|MS-PAR'` [[NOTE: from 2024, not yet checked]]
   Expected: if this returns results the system may be vulnerable.

## Evidence to capture
- `evidence/F-NNN-01.png`: the output showing the spooler's remote protocol is exposed on the host.
- The logged command with its timestamp.

## Practice
- **HTB box:** Sauna
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]
- **Practice credentials (practice data only, never use on game day):** [[TODO: move the Sauna credentials from the 2024 doc here]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
