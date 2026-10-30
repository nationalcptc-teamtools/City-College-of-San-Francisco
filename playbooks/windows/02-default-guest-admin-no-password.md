*Draft: command steps not filled in yet.*

# 2. Default Guest or Administrator Account Without a Password

- **Phase:** No credentials (check); Initial access (log in with the account)
- **Risk:** 🟡 Noisy: the check is itself a login, and Windows logs every login
- **Tier:** Recognize *(proposed)*
- **Finding:** library L20 (`default-credentials`) *(proposed)*
- **Runs on:** any Windows host
- **Ports:** 139, 445 (SMB)
- **Tools:** rpcclient, netexec (check); evil-winrm, xfreerdp, smbexec.py from Impacket (log in)

## What it is
Windows has built-in Guest and Administrator accounts. If either is enabled with a blank password, anyone on the network can log in as it. A blank Administrator password hands over the host.

The 2024 Runlist lists "Guest/Administrator" under No credentials but only "Guest" under Initial access. Check both.

## Commands
[[TODO: Copy the commands from the 2024 doc "2. Windows (Any) Default Guest Accounts Without Password.docx", split into the check and the login. Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Once it works
- Note what the account can reach (shares, remote login), then pass it to the team as a credential.

## Evidence to capture
- `evidence/F-NNN-01.png`: the successful login or session as the account, with the empty password visible in the command.
- The logged command with its timestamp.

## Practice
- **HTB box:** Archetype (Starting Point; needs the Starting Point VPN)
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
