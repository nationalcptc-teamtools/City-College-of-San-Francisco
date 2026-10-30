# Findings Library

Pre-written findings so we fill in specifics on the day instead of writing from scratch. **Each one is written the day you study the technique.** Writing the root cause, impact, and remediation is the test of whether you understood it.

**Study day:** replace every `[[TODO: …]]` marker with your own general text, then set the status to ◐.

**Competition day:** copy the library file to `findings/F-XXX-<slug>.md`, fill every `[[FIELD]]` with real evidence, delete the `[[NOTE: …]]` markers, and adjust the severity to context. The marker key is in `templates/README.md`.

| ID | Finding | Default severity | ATT&CK | CWE | Status |
|---|---|---|---|---|---|
| L01 | [Anonymous SMB/LDAP Access Exposes Domain Information](L01-anonymous-smb-ldap-access.md) | Medium | T1087.002 | CWE-284 | ☐ |
| L02 | [SNMP Uses Default Community String](L02-snmp-default-community.md) | Medium | T1602.001 | CWE-1392 | ☐ |
| L03 | [SMB Signing Not Required Allows NTLM Relay](L03-smb-signing-not-required.md) | Medium | T1557.001 | CWE-294 | ☐ |
| L04 | [Kerberoastable Service Account with Crackable Password](L04-kerberoastable-service-account.md) | High | T1558.003 | CWE-521 | ☐ |
| L05 | [Account Does Not Require Kerberos Pre-Authentication](L05-asrep-roastable-account.md) | High | T1558.004 | CWE-287 | ☐ |
| L06 | [Weak Domain Password Policy Permits Password Spraying](L06-weak-password-policy.md) | Medium | T1110.003 | CWE-521 | ☐ |
| L07 | [Excessive Privileges Create a Path to Domain Admin](L07-excessive-privilege-attack-path.md) | High (Critical path → use L13) | T1069.002 | CWE-269 | ☐ |
| L08 | [Dangerous Active Directory ACL Allows Account Takeover](L08-dangerous-ad-acl.md) | High | T1098 | CWE-732 | ☐ |
| L09 | [MSSQL Misconfiguration Allows Command Execution](L09-mssql-misconfiguration.md) | High | T1505.001 | CWE-250 | ☐ |
| L10 | [LLMNR/NBT-NS Enabled Allows Credential Capture](L10-llmnr-nbtns-poisoning.md) | Medium | T1557.001 | CWE-300 | ☐ |
| L11 | [Shared Local Administrator Password Enables Lateral Movement](L11-local-admin-password-reuse.md) | High | T1550.002 | CWE-262 | ☐ |
| L12 | [Vulnerable AD CS Certificate Template Allows Privilege Escalation](L12-adcs-vulnerable-template.md) | Critical | T1649 | CWE-295 | ☐ |
| L13 | [Full Active Directory Domain Compromise](L13-domain-compromise.md) | Critical | T1003.006 | CWE-269 | ☐ |
| L14 | [Local Privilege Escalation via Sudo/SUID Misconfiguration](L14-linux-privilege-escalation.md) | High | T1548.003 | CWE-250 | ☐ |
| L15 | [SQL Injection in Web Application](L15-sql-injection.md) | High | T1190 | CWE-89 | ☐ |
| L16 | [Insecure Direct Object Reference Exposes Other Users' Data](L16-idor-broken-access-control.md) | Medium | T1190 | CWE-639 | ☐ |
| L17 | [Weak Web Application Authentication Controls](L17-web-authentication-weakness.md) | Medium | T1110 | CWE-287 | ☐ |
| L18 | [Ride Control Network Reachable from Corporate/Guest Networks](L18-ot-network-segmentation.md) | High | ICS T0846 | CWE-923 | ☐ |
| L19 | [Industrial Protocol Accepts Unauthenticated Commands](L19-unauthenticated-industrial-protocol.md) | High | ICS T0855 | CWE-306 | ☐ |
| L20 | [Default Credentials on Administrative Interface](L20-default-credentials.md) | High | T1078.001 | CWE-1392 | ☐ |
| L21 | [Sensitive Services Use Cleartext Protocols](L21-cleartext-protocols.md) | Medium | T1040 | CWE-319 | ☐ |
| L22 | [Outdated and Unsupported Software in Use](L22-outdated-software.md) | Medium | T1190 | CWE-1104 | ☐ |

Default severities are starting points; set the final rating from what you demonstrated (`templates/severity-guide.md`). Keep the "Library text is general" note in a copied entry until you've checked every section against the real finding.

Statuses: ☐ not written, ◐ drafted, ☑ reviewed against a winning report.
