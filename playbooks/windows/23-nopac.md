*Draft: command steps not filled in yet.*

# 23. NoPac

- **Phase:** Escalation (low-privileged domain account)
- **Risk:** 🟢 Safe to check *(proposed)*. **The exploit is 🔴 Risky: it creates and renames a computer account and impersonates an administrator on the domain controller.** Approval every time.
- **Tier:** Recognize *(proposed)*
- **Finding:** none in the library yet
- **Runs on:** domain controllers, when unpatched (fixed November 2021)
- **Ports:** 88 (Kerberos)
- **Tools:** netexec, Impacket, noPac.py
- **You need:** a low-privileged username and password

## What it is
NoPac (CVE-2021-42278 and CVE-2021-42287) chains two flaws in how domain controllers handle computer account names, letting any domain user become a domain admin. It depends on users being able to add computers to the domain (#19).

A check shows whether the DC is unpatched without changing anything, which is enough for the finding.

## Commands
[[TODO: Copy the commands from the 2024 doc "23. Windows (DC, unpriv login) - NoPac.docx", with the scan first and the exploit marked as needing approval. Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the scan output showing the DC is vulnerable.
- If the exploit was approved and run: the result, plus a record of the computer account created, for cleanup.
- The logged commands with timestamps.

## Practice
- **HTB box:** Resolute
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
