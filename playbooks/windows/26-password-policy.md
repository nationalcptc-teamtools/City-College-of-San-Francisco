*Draft: command steps not filled in yet.*

# 26. Misconfigured Password Policy

- **Phase:** Low credentials. A null session sometimes shows the policy with no credentials (`checklists/10-ad-internal.md` step 2).
- **Risk:** 🟢 Safe *(proposed)*: reading the policy
- **Tier:** Must know *(proposed)*
- **Finding:** library L06 (`weak-password-policy`)
- **Runs on:** any Windows host; the domain policy lives on the domain controllers
- **Tools:** netexec; the 2024 Runlist also mentions exporting LDAP to HTML files (ldapdomaindump, as in #1)

## What it is
The domain's password policy sets the minimum length, complexity, maximum age and **lockout threshold**. A short minimum or no lockout makes guessing practical.

Read the policy before any password guessing. The lockout threshold sets how many guesses are safe: at most (threshold − 2) per observation window, per `checklists/10-ad-internal.md`. Locking out a client's users is an outage.

The 2024 Runlist's "still working out" block suggests widening this into password compliance as a whole (rotation and similar issues). [[TODO: decide whether to include that]]

## Commands
1. `netexec smb <TARGET_IP> --pass-pol` [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the policy output (minimum length, complexity, lockout threshold and window), with the domain visible.
- The logged command with its timestamp.

## Practice
- Practice: HTB **Cascade** (retired public box, `10.10.10.182`); the 2024 command targets it. [[TODO: no walkthrough in the 2024 doc; add one]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
