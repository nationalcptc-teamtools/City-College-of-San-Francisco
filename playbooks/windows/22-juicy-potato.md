*Draft: command steps not filled in yet.*

# 22. Juicy Potato

- **Phase:** Escalation (needs a shell on the host)
- **Risk:** 🔴 Risky: it escalates to SYSTEM and puts files on the client's host, and antivirus may flag them. Approval every time (matches `checklists/10-ad-internal.md`). Record what's dropped and remove it afterwards.
- **Tier:** Recognize *(proposed)*
- **Finding:** none in the library yet
- **Runs on:** Windows 7, 8, 8.1, 10; Server 2008, 2012, 2016 (older builds; fixed in later Windows 10 and Server 2019)

## What it is
Juicy Potato is a local privilege escalation: from a service account to SYSTEM on the same host. It works when the current account holds the **SeImpersonatePrivilege** right, which service accounts for IIS and SQL Server usually have.

The underlying finding is a service account with the impersonation right on an old Windows build; Juicy Potato is one way to prove it. On newer Windows, other "potato" tools do the same job. The 2024 Runlist parks God Potato (#24) as "still working out, may be too unstable".

## Commands
[[TODO: Copy the commands from the 2024 doc "22. Windows (any, low cred) - Juicy Potato_.docx". The 2024 doc puts the whole procedure under Practice, mixed with the box-specific foothold. Split it: the game-day part goes here; the Bounty-specific steps stay under Practice. Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the account's privileges showing SeImpersonatePrivilege.
- `evidence/F-NNN-02.png`: the result showing SYSTEM, if run.
- The logged commands with timestamps, and the list of files placed on the host.

## Practice
- **HTB box:** Bounty
- **Walkthroughs:** https://0xdf.gitlab.io/2018/10/27/htb-bounty.html, https://medium.com/@v1per/bounty-hackthebox-writeup-5b79a79e6de9
- [[TODO: the Bounty-specific steps from the 2024 doc, if worth keeping]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
