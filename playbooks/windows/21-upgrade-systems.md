*Draft: command steps not filled in yet.*

# 21. Upgrade End-of-Life Systems

- **Phase:** Low credentials (manual check); version scans show most of it with no credentials
- **Risk:** 🟢 Safe *(proposed)*: looking only
- **Tier:** Recognize
- **Finding:** L22 (`outdated-software`) *(proposed)*
- **Covers:** Windows XP, Vista, 7, 8, 8.1; Server 2003 through 2012

## What it is
Windows versions past end of life get no more security fixes, so every new flaw stays open. Any of the versions above is a finding on its own.

The 2024 doc adds a second check: on supported versions (Windows 10 and later, Server after 2012), make sure Windows Update isn't disabled.

The host's version usually shows up in the service scan already (`checklists/10-ad-internal.md` step 1), so this often needs no login.

## Commands
[[TODO: The 2024 doc "21. Windows (any) - Upgrade Systems.docx" has no commands. Add a version check and a Windows Update check, in the format of `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the scan output or system information showing the Windows version, with the hostname visible.

## Practice
- [[TODO: none in the 2024 doc; any of the HTB boxes above running an old Windows version works (Blue, for example)]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
