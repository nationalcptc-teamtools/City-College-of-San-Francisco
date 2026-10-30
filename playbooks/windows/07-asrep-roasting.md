*Draft: command steps not filled in yet.*

# 7. Kerberos Pre-Authentication Disabled (AS-REP Roasting)

- **Phase:** No credentials (short scan); Initial access (long scan)
- **Risk:** 🟡 Noisy: every ticket request is logged on the domain controller, whatever the list length. No account lockouts (2024 note).
- **Tier:** Must know *(proposed)*
- **Finding:** library L05 (`asrep-roastable-account`)
- **Runs on:** AD domain controllers running Kerberos, Server 2008 through 2022
- **Ports:** 88 (Kerberos)
- **Tools:** GetNPUsers.py (Impacket)
- **You need:** the AD domain name (e.g. `active.htb`); a list of likely usernames

## What it is
Kerberos is how users log in to an AD domain. Normally a user must prove they know the password before the DC sends anything back; that's **pre-authentication**. Some accounts have it turned off, often for old software.

For those accounts, anyone can ask the DC for a login reply, which comes back encrypted with the user's password. It can be cracked offline, so there are no failed logins and no lockouts.

The 2024 doc's notes:
- Try usernames found on other systems as well as the wordlists.
- The hashes may not crack during the competition. If not, still report the setting, and note a strong password as a positive in the report.

**Short vs. long scan:** the 2024 Runlist runs a short username list during the no-credentials scans, and a long list later as an initial-access attempt.

## Commands
[[TODO: Copy the commands from the 2024 doc "7. Windows - (AD) - Kerberos Pre-Authentication Disabled.docx", including the two username wordlist paths. Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Once a hash is found
- Crack it offline. If it cracks, pass the credential to the team.

## Evidence to capture
- `evidence/F-NNN-01.png`: the output showing the account and the returned hash (redact all but the first and last characters).
- `evidence/F-NNN-02.png`: the cracked password, redacted the same way, if it cracked.
- The logged commands with timestamps.

## Practice
- **HTB boxes:** Active (domain `active.htb`), Forest (domain `local.htb`, per the 2024 doc)
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
