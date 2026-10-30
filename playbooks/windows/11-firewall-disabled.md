*Draft: commands copied from 2024, not yet checked.*

# 11. Windows Firewall Disabled

- **Phase:** Low credentials (manual check over RDP)
- **Risk:** 🟢 Safe: looking only
- **Tier:** Reference
- **Finding:** none in the library yet
- **Runs on:** any Windows host
- **You need:** low-privileged credentials; Remote Desktop access

## What it is
Windows Defender Firewall limits which services on a host can be reached from the network. With it off, every listening service is exposed, which makes other weaknesses reachable.

Check all three profiles (Domain, Private, Public); a host can be off in one and on in the others.

## Commands
1. Open `Windows Defender Firewall` from Windows Search. [[NOTE: from 2024, not yet checked]]
2. If the Windows Defender Firewall state is off, it is a finding. [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the firewall screen or command output showing the state is off, with the hostname visible.

## Practice
- **Local VM:** Windows Search → "Windows Defender Firewall"; the state shows as off (2024 doc).

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
