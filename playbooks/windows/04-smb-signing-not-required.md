*Draft: command steps not filled in yet.*

# 4. SMB Signing Not Required

- **Phase:** No credentials (scan only)
- **Risk:** 🟢 Safe: a configuration check
- **Tier:** Must know
- **Finding:** library L03 (`smb-signing-not-required`)
- **Runs on:** any Windows version; older ones (XP through Server 2012) are the most likely, but check every host
- **Ports:** 139, 445 (SMB)
- **Tools:** nmap

## What it is
SMB signing adds a signature to each message so an attacker in the middle can't tamper with or replay it. If signing is not *required*, an attacker who captures a login attempt can pass it to that host and get in as that user. That's an **NTLM relay**.

The finding is the missing requirement. Relaying is a separate, riskier step (see #8 and `checklists/10-ad-internal.md`), and only if the RoE allows it.

Domain controllers require signing by default; workstations and member servers often don't. The scan output says either "disabled" or "not required": both count.

## Commands
1. `nmap --script smb2-security-mode -p 445 <TARGET_IP>` [[NOTE: from 2024, not yet checked]]
   Expected: will say "disabled" or "not required".

## Evidence to capture
- `evidence/F-NNN-01.png`: the scan output showing signing "enabled but not required" (or disabled), with the host list.
- The logged command with its timestamp.

## Practice
- **HTB box:** Atom
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
