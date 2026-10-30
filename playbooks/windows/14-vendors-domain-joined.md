*Draft: command steps not filled in yet.*

# 14. Vendor Machines Are Domain-Joined

- **Phase:** SYSTEM credentials (2024 Runlist); the 2024 doc says an unprivileged login is enough (manual check over RDP)
- **Risk:** 🟢 Safe: looking only
- **Tier:** Reference
- **Finding:** none in the library yet
- **Runs on:** domain controllers
- **Ports:** none (RDP)
- **Tools:** Windows RDP

## What it is
Outside vendors' machines (a support company's laptop, a supplier's appliance) should not be full members of the client's domain. A domain-joined vendor machine trusts the domain and the domain trusts it, so a compromise at the vendor becomes a way into the client's network.

Look for computer or user objects named after vendors, or kept in a vendor organizational unit.

The 2024 file name says "unpriv login" but the 2024 Runlist puts it under SYSTEM credentials. [[TODO: check which access level is actually needed]]

## Commands
1. Open `Active Directory Users and Computers (ADUC)`. [[NOTE: from 2024, not yet checked]]
2. Click the `Computers` container or an OU container; computers are stored here. Any computer listed is domain joined; if it is a vendor, it is a finding. [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the AD screen or output listing the vendor machines in the domain.

## Practice
- **Local:** a Windows Server 2022 practice domain (2024 doc).

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
