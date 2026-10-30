### [[FINDING_ID]]: SMB Signing Not Required Allows NTLM Relay

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L03, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-smb-signing-not-required.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a position on the same network and a way to get a victim machine to connect to the attacker (easy where name lookups can be tricked; see the LLMNR entry). Tools are widely available. Likely on internal networks.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-294, ATT&CK T1557.001, https://learn.microsoft.com/en-us/windows-server/storage/file-server/smb-signing-overview

#### Summary
Some Windows machines do not insist that file-sharing (SMB) messages are signed. An attacker on the network can sit between a user and a server and pass the user's login along as their own, gaining access without learning the password.

#### Business impact
One captured login from a normal user can become access to file servers, workstations or databases. If the relayed account is an administrator, the attacker can gain control of those machines. This is a common stepping stone to wider compromise. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
SMB signing proves each message came from the real sender and was not changed. When signing is supported but not required, a server accepts unsigned sessions. In an NTLM relay, the attacker forwards a victim's authentication to a target that does not require signing, and the target treats the attacker as the victim. Domain controllers require signing by default in current Windows; member servers and workstations often do not.

#### Reproduction steps
1. Scan the in-scope hosts and list each one's SMB signing status.
   Expected: Hosts show signing as enabled but not required, or as required.
2. Record the hosts where signing is not required, ranked by role (file server, workstation, server with admin users).
   Expected: A host list for the finding's affected assets.
3. Only if the rules of engagement allow it, show that a relayed login is accepted on one low-risk target, using a test account.
   Expected: The target accepts the relayed session. If not done, rate as configuration only.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** On every server and workstation, set Group Policy "Microsoft network server: Digitally sign communications (always)" and "Microsoft network client: Digitally sign communications (always)" to Enabled.
- **Longer term:** Reduce NTLM use (audit it, then restrict it), prefer Kerberos, turn off LLMNR and NBT-NS, and put the signing setting in the standard server and workstation build.
- **How to verify the fix:** Re-run the signing scan: every host should report signing as required. Confirm with Get-SmbServerConfiguration (RequireSecuritySignature is True).

#### Detection (for the client's defenders)
Look for NTLM network logons (event 4624, logon type 3) where the source address does not match the workstation name, and one source authenticating to many hosts quickly. NTLM auditing (events 8001-8004 in the NTLM operational log) improves visibility.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
