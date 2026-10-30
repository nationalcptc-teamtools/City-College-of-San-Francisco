*Draft: command steps not filled in yet.*

# 13. Sensitive Information in Active Directory Comments

- **Phase:** Low credentials
- **Risk:** 🟢 Safe *(proposed)*: read-only directory queries
- **Tier:** Must know *(proposed)*
- **Finding:** none in the library yet. L01 covers the anonymous case (#1).
- **Runs on:** AD domain controllers
- **Tools:** ldapsearch, or xfreerdp plus "Active Directory Users and Computers"
- **You need:** a low-privileged username and password; the AD domain name

## What it is
AD users and computers have free-text fields like **description** and **info**. Admins sometimes put passwords there ("temp password: ...") and forget that every domain user can read them.

This is #1 with a login: #1 covers what an anonymous user can read, #13 what any domain user can read, which is far more. Run it as soon as we have a first credential. `checklists/10-ad-internal.md` calls passwords in descriptions "a classic".

## Commands
ldapsearch way:

1. `ldapsearch -H ldap://<TARGET_IP> -D '<USER>@<DOMAIN>' -w "<PASSWORD>" -b "dc=<CHANGE>,dc=<CHANGE>" "(objectClass=user)" description | grep description` [[NOTE: from 2024, not yet checked]]

RDP way:

1. Use xfreerdp or another RDP client to log in as an unprivileged (or privileged) user. [[NOTE: from 2024, not yet checked]]
2. In Run, open `Active Directory Users and Computers` and look at the users' comments. [[NOTE: from 2024, not yet checked]]

## Once a secret is found
- If it's a password, check it with a single login (mind the lockout policy, #26), then pass it to the team.

## Evidence to capture
- `evidence/F-NNN-01.png`: the output or screen showing the account and the field holding the secret (redact all but the first and last characters).
- The logged command with its timestamp.

## Practice
- **HTB box:** Search
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]
- The 2024 doc notes an RDP practice box was never found.

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
