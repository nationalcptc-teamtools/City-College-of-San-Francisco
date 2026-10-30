*Draft: command steps not filled in yet.*

# 6. ZeroLogon

- **Phase:** No credentials (scan only)
- **Risk:** The tester is 🟡 Noisy: it changes nothing, but the domain controller logs every attempt. **The exploit is Prohibited: it resets the domain controller's machine password, which breaks the domain. Run the tester only.**
- **Tier:** Must know, at check level only
- **Finding:** library L22 (`outdated-software`)
- **Runs on:** domain controllers, Server 2008 through 2022, when unpatched
- **Ports:** 135, 445
- **Tools:** `zerologon_tester.py` from https://github.com/SecuraBV/CVE-2020-1472
- **You need:** the DC's NetBIOS computer name

## What it is
ZeroLogon (CVE-2020-1472) is a flaw in how domain controllers authenticate computers. On an unpatched DC, anyone on the network can take over the DC's own computer account.

**Why verify only:** the public exploit resets the DC's computer password. The DC falls out of sync with the domain and logins can break until it's repaired: an outage we caused. The 2024 doc says the same: "If actual compromise is needed for access, get permission first."

The tester script only checks whether the DC is vulnerable and changes nothing (2024 note). That's enough for a critical finding.

The 2024 doc spells it "ZeroLogin"; the standard name is ZeroLogon.

## Commands
1. `enum4linux <TARGET_IP>` (to get the NetBIOS computer name of the DC) [[NOTE: from 2024, not yet checked]]
2. `python3 zerologon_tester.py <NETBIOS_DC_NAME> <TARGET_IP>` [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the tester script's output saying the DC is vulnerable.
- The logged command with its timestamp.

## Practice
- **HTB box:** Active (NetBIOS computer name: DC)
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
