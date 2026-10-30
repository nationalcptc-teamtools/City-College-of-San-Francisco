### [[FINDING_ID]]: Anonymous SMB/LDAP Access Exposes Domain Information

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L01, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-anonymous-smb-ldap-access.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Anyone who can reach the domain controller or a file server can try it, including a visitor on a guest or flat office network. No account is needed. Common on older or default-configured domains.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-284, ATT&CK T1087.002, https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/anonymous-ldap-operations-active-directory-disabled

#### Summary
Some servers answer questions without asking who is asking. Anyone on the network can list user names, groups and shared folders, which gives an attacker a ready-made target list for password guessing and phishing.

#### Business impact
Exposed user and group lists make later attacks faster, and shares that allow anonymous reads can leak internal documents. The exposure rarely causes a breach alone, but it removes a layer of defence. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Windows can allow "null sessions" (SMB connections with no user name) and anonymous LDAP reads. This happens when legacy settings are on, when the anonymous access group is added to share or directory permissions, or when LDAP accepts unauthenticated binds. The server then returns the user list, group membership, password policy and share names to any caller. Root cause: access control that trusts network position instead of requiring a login.

#### Reproduction steps
1. From a machine on the same network, with no credentials, ask the server for its list of shared folders using an anonymous (empty user name) connection.
   Expected: The server lists shares or refuses with access denied. A list confirms the finding.
2. Try an anonymous directory query against the domain controller for the user list.
   Expected: User or group names come back without a login. An error saying authentication is required means this part is not vulnerable.
3. Record which shares can be read and which names were returned. Do not open or copy file contents beyond what proves access.
   Expected: A short list of names and shares for the evidence file.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Disable anonymous access: set "Network access: Restrict anonymous access to Named Pipes and Shares" to Enabled, turn on "Do not allow anonymous enumeration of SAM accounts and shares", and make the domain controller refuse anonymous LDAP binds (do not add Anonymous Logon to directory permissions). Remove "Everyone" and "Anonymous Logon" from share permissions.
- **Longer term:** Manage these settings through Group Policy, review share permissions on a schedule, and keep servers on current Windows versions where the safe defaults apply.
- **How to verify the fix:** Repeat the anonymous share list and directory query from a test machine. Both should fail with access denied or authentication required. Check the Group Policy result on the server.

#### Detection (for the client's defenders)
Look for network logons by the ANONYMOUS LOGON account (event 4624) and failed or odd bind attempts in the directory service log. Repeated share and name listings from one source in a short time suggest scanning.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
