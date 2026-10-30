*Draft: commands copied from 2024, not yet checked.*

# 15. Workstation Accounts Have the Administrator Role

- **Phase:** SYSTEM credentials (manual check over RDP)
- **Risk:** 🟢 Safe *(proposed)*: looking only
- **Tier:** Recognize
- **Finding:** L07 (`excessive-privilege-attack-path`) *(proposed)*
- **Runs on:** any Windows host; domain controllers
- **Tools:** RDP
- **You need:** an Administrator username and password

## What it is
Everyday user accounts on workstations should not be local administrators. Admin rights let a user install software, turn off security tools and read other users' credentials from memory, and any malware they run gets the same rights.

Check both places the 2024 doc covers: AD group membership, and the local Administrators group on a workstation.

## Commands
Domain controller:

1. Open `Active Directory Users and Computers`. [[NOTE: from 2024, not yet checked]]
2. Go to `Domain Admins` and inspect the `Members` tab for regular user accounts that should not be administrators. [[NOTE: from 2024, not yet checked]]

Workstations:

1. Open `Local Users and Groups`. [[NOTE: from 2024, not yet checked]]
2. Inspect the `Administrators` group properties for regular user accounts that should not be administrators. [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the group membership showing ordinary user accounts in an administrator group, with the host or domain visible.

## Practice
- **Local:** an AD practice domain and a Windows workstation (the 2024 doc used Windows 8).

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
