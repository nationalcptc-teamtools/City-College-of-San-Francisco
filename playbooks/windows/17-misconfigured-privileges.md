*Draft: command steps not filled in yet.*

# 17. Accounts with Misconfigured Privileges

- **Phase:** Low credentials (LDAP, or manual check over RDP)
- **Risk:** 🟢 Safe *(proposed)*: read-only queries. BloodHound with `-c All` is 🟡 Noisy: it connects to every computer. **Any change to an AD object (abusing the right) is 🔴 Risky:** approval every time.
- **Tier:** Recognize
- **Finding:** L07 (`excessive-privilege-attack-path`) or L08 (`dangerous-ad-acl`) *(proposed)*
- **Runs on:** any Windows host; domain controllers
- **Tools:** ldapdomaindump (the 2024 doc says "ldapdomainsearch"), RDP
- **You need:** LDAP access with a domain account, or an RDP login

## What it is
Accounts end up with more rights than their job needs: a service account in Domain Admins, a help-desk group that can reset admin passwords. Each is a shortcut for an attacker.

BloodHound finds these as attack paths (`training/technique-map.md`; `checklists/10-ad-internal.md` step 3). This playbook is the manual version.

## Commands
[[TODO: Copy the steps from the 2024 doc "17. Accounts with Misconfigured Privileges.docx". Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the output showing the account and the group or right it shouldn't have.
- The logged command with its timestamp.

## Practice
- [[TODO: none in the 2024 doc; add a box or local setup]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
