*Draft: command steps not filled in yet.*

# 3. SMBv1 Enabled

- **Phase:** No credentials (scan only)
- **Risk:** 🟢 Safe: a version check
- **Tier:** Recognize
- **Finding:** library L22 (`outdated-software`)
- **Runs on:** Windows XP, 7, early Windows 10, Server 2016; later versions have it off by default but can turn it on
- **Ports:** 139, 445 (SMB)
- **Tools:** nmap

## What it is
SMB is Windows' file-sharing protocol. Version 1 is decades old and deprecated by Microsoft. Several of the worst Windows bugs, EternalBlue (#9) among them, only work over SMBv1. Having it enabled is a finding on its own.

If SMBv1 is on, check #9 (EternalBlue) on the same host.

## Commands
1. `nmap --script smb-protocols -p 445 <TARGET_IP>` [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the scan output showing SMBv1 (often listed as "NT LM 0.12") among the supported dialects.
- The logged command with its timestamp.

## Practice
- **HTB box:** Atom
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
