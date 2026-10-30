*Draft: commands copied from 2024, not yet checked.*

# 12. Windows Real-Time Protection Disabled

- **Phase:** Low credentials (manual check over RDP)
- **Risk:** 🟢 Safe: looking only
- **Tier:** Reference
- **Finding:** none in the library yet
- **Runs on:** any Windows host
- **You need:** low-privileged credentials; Remote Desktop access

## What it is
Real-time protection is the part of Microsoft Defender Antivirus that scans files as they're opened or downloaded. With it off, malware runs without being stopped or reported.

It's often switched off "temporarily" for troubleshooting and never switched back on. A third-party antivirus also turns Defender off on purpose; if one is installed, check whether *that* product is running instead.

## Commands
1. Open `Windows Security` from Windows Search. [[NOTE: from 2024, not yet checked]]
2. Look at the `Virus and threat protection` setting; if it is disabled it is a finding. [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the Windows Security screen or command output showing real-time protection off, with the hostname visible.

## Practice
- **Local VM:** Windows Search → "Windows Security" (2024 doc).

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
