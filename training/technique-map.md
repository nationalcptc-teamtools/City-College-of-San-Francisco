# Technique Map

Pick practice topics here; each technique links to its playbooks, checklists and draft finding.

**Priority:** how often a technique showed up in reviewed competition material.
- **Common:** appeared broadly
- **Sometimes:** appeared repeatedly
- **Rare:** only occasionally or in narrow environments

It's a training signal, not a guarantee a technique will recur.

⚠️ **Safety:** follow the Rules of Engagement and the linked playbooks. Approval-gated, disruptive or scope-sensitive techniques stay off until the client or Operations approves in writing. Log it in `NOTE-approvals.md` (Recon Field Guide 1.1).

## Reconnaissance and common findings

| Technique | ATT&CK | Tools | Priority | Study path | Library finding |
|---|---|---|---|---|---|
| Network service discovery | T1046 | Nmap | Common | [Recon playbooks](../playbooks/recon/) | Supports all findings |
| SNMP enumeration (default community strings) | T1602.001 | Nmap scripts, snmpwalk, onesixtyone | Sometimes | [Recon playbooks](../playbooks/recon/) | [L02 SNMP default community](../findings-library/drafts/L02-snmp-default-community.md) |
| Mail service enumeration (SMTP user enumeration, open relay) | T1087 | Nmap, swaks, smtp-user-enum | Sometimes | [Recon playbooks](../playbooks/recon/) | Note only |
| Default credentials | T1078.001 | Manual review, vendor documentation | Common | [General playbooks](../playbooks/general/) | [L20 default credentials](../findings-library/drafts/L20-default-credentials.md) |
| Cleartext protocols (HTTP, FTP, Telnet) | T1040 | Nmap, Wireshark | Common | [Recon playbooks](../playbooks/recon/) | [L21 cleartext protocols](../findings-library/drafts/L21-cleartext-protocols.md) |
| Outdated or unsupported software | T1190 | Nmap service detection, version research | Common | [Recon playbooks](../playbooks/recon/) | [L22 outdated software](../findings-library/drafts/L22-outdated-software.md) |

## Windows and Active Directory

| Technique | ATT&CK | Tools | Priority | Study path | Library finding |
|---|---|---|---|---|---|
| SMB, LDAP, and RPC enumeration (null and guest sessions) | T1087.002, T1069.002 | NetExec, smbclient, smbmap, enum4linux-ng, ldapsearch, ldapdomaindump | Common | [Windows playbooks](../playbooks/windows/), [AD checklist](../checklists/10-ad-internal.md) | [L01 anonymous SMB and LDAP access](../findings-library/drafts/L01-anonymous-smb-ldap-access.md) |
| Username enumeration via Kerberos | T1087.002 | Kerbrute | Common | [Windows playbooks](../playbooks/windows/) | Supports L04 and L05 |
| Kerberoasting | T1558.003 | GetUserSPNs.py, NetExec, hashcat | Common | [Kerberoasting playbook](../playbooks/windows/25-kerberoasting.md) | [L04 kerberoastable service account](../findings-library/drafts/L04-kerberoastable-service-account.md) |
| AS-REP roasting | T1558.004 | GetNPUsers.py, NetExec, hashcat | Common | [AS-REP roasting playbook](../playbooks/windows/07-asrep-roasting.md) | [L05 AS-REP roastable account](../findings-library/drafts/L05-asrep-roastable-account.md) |
| Password spraying (policy-aware) | T1110.003 | NetExec, Kerbrute | Sometimes | [Password policy playbook](../playbooks/windows/26-password-policy.md) | [L06 weak password policy](../findings-library/drafts/L06-weak-password-policy.md) |
| BloodHound attack-path analysis | T1069.002, T1087.002 | BloodHound collector, BloodHound CE | Common | [Windows playbooks](../playbooks/windows/), [AD checklist](../checklists/10-ad-internal.md) | [L07 excessive privilege attack path](../findings-library/drafts/L07-excessive-privilege-attack-path.md) |
| ACL abuse (GenericAll, WriteDACL, ForceChangePassword) | T1098 | BloodHound, bloodyAD, dacledit.py | Sometimes | [Misconfigured privileges playbook](../playbooks/windows/17-misconfigured-privileges.md) | [L08 dangerous AD ACL](../findings-library/drafts/L08-dangerous-ad-acl.md) |
| MSSQL abuse (xp_cmdshell, impersonation, linked servers) | T1505.001 | mssqlclient.py, NetExec | Sometimes | [Windows playbooks](../playbooks/windows/) | [L09 MSSQL misconfiguration](../findings-library/drafts/L09-mssql-misconfiguration.md) |
| LLMNR/NBT-NS poisoning | T1557.001 | Responder in analysis mode first | Common | [Windows playbooks](../playbooks/windows/) | [L10 LLMNR and NBT-NS poisoning](../findings-library/drafts/L10-llmnr-nbtns-poisoning.md) |
| SMB relay (signing not required) | T1557.001 | NetExec, ntlmrelayx.py | Common | [SMB signing playbook](../playbooks/windows/04-smb-signing-not-required.md) | [L03 SMB signing not required](../findings-library/drafts/L03-smb-signing-not-required.md) |
| Authentication coercion (PetitPotam and related methods) | T1187 | PetitPotam, Coercer | Sometimes | [PetitPotam playbook](../playbooks/windows/08-petitpotam.md) | Supports L03 and L12 |
| Credential reuse / local administrator reuse (no LAPS) | T1078.003, T1550.002 | NetExec, secretsdump.py | Common | [Windows playbooks](../playbooks/windows/) | [L11 local administrator password reuse](../findings-library/drafts/L11-local-admin-password-reuse.md) |
| Remote execution (WinRM, SMB, WMI) | T1021.006, T1021.002, T1047 | Evil-WinRM, wmiexec.py, psexec.py | Sometimes | [Windows playbooks](../playbooks/windows/) | Supports L11 |
| ADCS template abuse (ESC1, ESC8) | T1649 | Certipy | Sometimes | [Windows playbooks](../playbooks/windows/) | [L12 ADCS vulnerable template](../findings-library/drafts/L12-adcs-vulnerable-template.md) |
| DCSync / domain compromise | T1003.006 | secretsdump.py | Sometimes | [Windows playbooks](../playbooks/windows/) | [L13 domain compromise](../findings-library/drafts/L13-domain-compromise.md) |
| GPO abuse | T1484.001 | pyGPOAbuse | Sometimes | [Windows playbooks](../playbooks/windows/) | Note only |
| Kerberos delegation abuse (unconstrained, constrained, RBCD) | T1558 | BloodHound, findDelegation.py, getST.py, rbcd.py, NetExec | Common | [Windows playbooks](../playbooks/windows/) | Candidate finding |
| Shadow credentials (KeyCredentialLink write) | T1098 | Certipy, pywhisker | Sometimes | [Windows playbooks](../playbooks/windows/) | Note only |

## Web applications

| Technique | ATT&CK / ATLAS | Tools | Priority | Study path | Library finding |
|---|---|---|---|---|---|
| Web: SQL injection | T1190 | Burp Suite, sqlmap at low intensity | Sometimes | [SQL injection playbook](../playbooks/web/13-sql-injection.md), [web checklist](../checklists/20-web-app.md) | [L15 SQL injection](../findings-library/drafts/L15-sql-injection.md) |
| Web: IDOR / broken access control | T1190 | Burp Suite | Common | [Web playbooks](../playbooks/web/), [web checklist](../checklists/20-web-app.md) | [L16 IDOR and broken access control](../findings-library/drafts/L16-idor-broken-access-control.md) |
| Web: authentication weaknesses | T1110, T1078 | Burp Suite, Hydra when permitted | Sometimes | [Web playbooks](../playbooks/web/), [web checklist](../checklists/20-web-app.md) | [L17 web authentication weakness](../findings-library/drafts/L17-web-authentication-weakness.md) |
| LLM jailbreak and prompt injection (chatbots, language-model password managers) | ATLAS AML.T0054, AML.T0051 | Manual prompts, Burp Suite for API review | Common | [Web playbooks](../playbooks/web/) | Candidate finding |
| URL-fetch features abused for file read or SSRF | T1190 | Burp Suite | Common | [SSRF playbook](../playbooks/web/12-ssrf.md) | Covered by the web checklist |

## Linux privilege escalation and pivoting

| Technique | ATT&CK | Tools | Priority | Study path | Library finding |
|---|---|---|---|---|---|
| Linux privilege escalation (sudo, SUID, cron, credentials in files) | T1548.003, T1548.001, T1552.001 | PEASS-ng, pspy, GTFOBins | Common | [General playbooks](../playbooks/general/) | [L14 Linux privilege escalation](../findings-library/drafts/L14-linux-privilege-escalation.md) |
| Pivoting / tunneling | T1572, T1090 | Ligolo-ng, Chisel, ProxyChains, SSH tunneling | Common | [General playbooks](../playbooks/general/) | Methodology, not a finding |

## Operational technology

| Technique | ATT&CK | Tools | Priority | Study path | Library finding |
|---|---|---|---|---|---|
| OT network reachability / segmentation | ICS T0846 | Nmap with slow, specific TCP checks | Rare | [IT-to-OT reachability playbook](../playbooks/ot/04-it-to-ot-reachability.md), [OT checklist](../checklists/30-ot-ics-safe.md) | [L18 OT network segmentation](../findings-library/drafts/L18-ot-network-segmentation.md) |
| Unauthenticated industrial protocols (Modbus, BACnet, S7) | ICS T0846; impact T0855 | Read-only Nmap protocol checks | Rare | [OT playbooks](../playbooks/ot/), [OT checklist](../checklists/30-ot-ics-safe.md) | [L19 unauthenticated industrial protocol](../findings-library/drafts/L19-unauthenticated-industrial-protocol.md) |

## Cloud and social engineering scenarios

| Technique | ATT&CK | Tools | Priority | Study path | Library finding |
|---|---|---|---|---|---|
| Cloud storage and identity enumeration (public blobs or buckets holding credentials) | T1530, T1580 | AzureHound, Azure CLI, MicroBurst | Common | [Web playbooks](../playbooks/web/), [general playbooks](../playbooks/general/) | Candidate finding |
| Phishing with a macro document (only if in scope) | T1566.001 | Office macro with an approved test payload | Common | [General playbooks](../playbooks/general/) | Note only |
| Voice vishing of a helpdesk (only if in scope) | T1566.004 | Client-provided communication platform | Common | [General playbooks](../playbooks/general/) | Note only |

## Deliberately de-emphasized

Recognition topics, not baseline practice:
- C2 frameworks
- AV-evasion loaders
- custom collaboration web applications
- direct exploitation of old named vulnerabilities

Spend the time on Common and Sometimes techniques, unless the Rules of Engagement or target evidence change the priority.

**Common first, then Sometimes.**
