*Draft: command steps not filled in yet.*

# 9. EternalBlue

- **Phase:** No credentials (scan only)
- **Risk:** 🟢 Safe to check *(proposed)*. **Exploiting is 🔴 Risky: scan only, do not exploit**.
- **Tier:** Must know, at check level only *(proposed)*
- **Finding:** library L22 (`outdated-software`) *(proposed)*
- **Runs on:** Windows XP, Vista, 7, 8, 8.1; Server 2003 through 2012 R2, when unpatched
- **Ports:** 139, 445 (SMB)
- **Tools:** nmap

## What it is
EternalBlue (MS17-010) is a remote code execution bug in SMBv1, behind the WannaCry and NotPetya outbreaks. An unpatched host with SMBv1 on (#3) can be taken over from the network with no credentials.

**Why scan only:** the exploit corrupts kernel memory, and a failed attempt can crash the host (blue screen). A vulnerable scan result is enough for a critical finding.

## Commands
1. `nmap --script smb-vuln-ms17-010 -p 445 <TARGET_IP>` [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the scan output marking the host as vulnerable to MS17-010.
- The logged command with its timestamp.

## Practice
- **HTB box:** Blue
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
