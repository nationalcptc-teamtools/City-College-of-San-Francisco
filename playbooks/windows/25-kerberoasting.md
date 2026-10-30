*Draft: command steps not filled in yet.*

# 25. Kerberoasting

- **Phase:** Escalation (any domain account)
- **Risk:** 🟡 Noisy: the ticket requests are ordinary but logged, and many at once trip standard alerts. Cracking happens offline.
- **Tier:** Must know *(proposed)*
- **Finding:** library L04 (`kerberoastable-service-account`)
- **Runs on:** AD domain controllers running Kerberos, Server 2008 through 2022
- **Ports:** 88 (Kerberos)
- **Tools:** GetUserSPNs.py (Impacket)
- **You need:** a username plus password or NTLM hash; the AD domain name

## What it is
Services in a domain (SQL Server, web apps) run under accounts that have a **service principal name (SPN)**. Any domain user may ask the DC for a ticket to such a service, and part of that ticket is encrypted with the service account's password.

Crack the ticket offline: if the password is weak, you get it. Service accounts often have broad rights and passwords that never change, so this is one of the most common paths to domain admin.

As with #7, an uncracked hash still means the setting is exposed. Report it and note a strong password as a positive.

## Commands
[[TODO: Copy the commands from the 2024 doc "25. Windows (AD Kerberos, credentials needed) - Kerberoasting.docx". Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Once a hash cracks
- Check what the service account can reach, then pass the credential to the team.

## Evidence to capture
- `evidence/F-NNN-01.png`: the output listing the service accounts and their SPNs.
- `evidence/F-NNN-02.png`: the cracked password, redacted to its first and last characters, if it cracked.
- The logged commands with timestamps.

## Practice
- **HTB box:** Active (domain `active.htb`)
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]
- **Practice credentials (practice data only, never use on game day):** [[TODO: move the Active credentials from the 2024 doc here]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
