*Draft: command steps not filled in yet.*

# 20. Shutdown Without Login

- **Phase:** Low credentials (manual check over RDP)
- **Risk:** 🟢 Safe to check *(proposed)*. **Never click shut down: that takes a client machine offline (🔴 Risky).**
- **Tier:** Reference *(proposed)*
- **Finding:** none in the library yet
- **Runs on:** any Windows host
- **Ports:** RDP
- **You need:** a low-privileged username and password

## What it is
Windows can show a shut-down button on the login screen. Anyone at the console can then turn the machine off without an account, an easy outage on a server.

The check is whether the button is there (or the matching policy is set), not whether it works.

## Commands
1. Log in to Windows over RDP. [[NOTE: from 2024, not yet checked]]
2. Type `gpedit` into the search box. [[NOTE: from 2024, not yet checked]]
3. Go to `Computer Configuration -> Windows Settings -> Security Settings -> Local Policies -> Security Options`. [[NOTE: from 2024, not yet checked]]
4. If `Shutdown: Allow the system to be shutdown without having to log on` is Enabled, the system is vulnerable. [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the login screen showing the shut-down option, or the policy setting, with the hostname visible.

## Practice
- [[TODO: none in the 2024 doc; a local Windows VM works]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
