*Draft: commands copied from 2024, not yet checked.*

# 19. Authenticated Users Can Add Workstations to the Domain

- **Phase:** SYSTEM credentials (2024 Runlist); the 2024 file name says Administrator credentials (manual check over RDP)
- **Risk:** 🟢 Safe to check. Actually adding a computer to the domain changes the client's AD: 🔴 Risky.
- **Tier:** Recognize
- **Finding:** none in the library yet
- **Runs on:** domain controllers
- **Tools:** RDP

## What it is
By default, any domain user can join up to 10 computers to the domain. That's the `ms-DS-MachineAccountQuota` setting. An attacker with any domain login can add a machine they control, which several escalation attacks need, NoPac (#23) among them.

The finding is the setting itself. Reading it is enough; don't add a computer to prove it.

## Commands
1. `Run -> gpmc.msc` [[NOTE: from 2024, not yet checked]]
2. In GPMC expand the domain, go to `Group Policy Objects`, right-click `Default Domain Controllers Policy` and select `Edit`. [[NOTE: from 2024, not yet checked]]
3. Go to `Computer Configuration > Policies > Windows Settings > Security Settings > Local Policies > User Rights Assignment`. [[NOTE: from 2024, not yet checked]]
4. Double-click `Add workstations to domain`. [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the setting or policy showing that authenticated users can add workstations, with the domain visible.

## Practice
- **Local:** a practice domain controller (2024 doc).

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
