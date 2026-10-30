*Draft: commands copied from 2024, not yet checked.*

# 16. Internet Explorer Enabled

- **Phase:** Low credentials (manual check over RDP)
- **Risk:** 🟢 Safe *(proposed)*: looking only
- **Tier:** Reference *(proposed)*
- **Finding:** L22 (`outdated-software`) *(proposed)*
- **Runs on:** Windows 95 through Windows 10
- **Tools:** RDP

## What it is
Internet Explorer is retired and gets no security fixes. A host that can still open it can be attacked through any web page a user visits. It should be removed or disabled (Edge replaces it).

## Commands
1. `Run -> optionalfeatures` [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: Internet Explorer open on the host, or the setting showing it enabled, with the hostname visible.

## Practice
- **Local:** a Windows VM (the 2024 doc used Windows 8).

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
