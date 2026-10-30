### [[FINDING_ID]]: Full Active Directory Domain Compromise

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L13, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-domain-compromise.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Critical [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Once an attacker has Domain Admin or equivalent, the remaining steps are easy and well documented. The chance of getting there depends on how many earlier weaknesses exist. In weakly managed domains the path from first foothold is often hours.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-269, ATT&CK T1003.006, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/best-practices-for-securing-active-directory

#### Summary
We took control of the whole Active Directory domain: we could sign in as any user, read or change any account and reach any domain-joined computer. This finding ties together the earlier weaknesses that made it possible.

#### Business impact
Control of the directory means control of staff logins, email, file servers and the systems that depend on them. An attacker at this level can steal data, disrupt operations or deploy ransomware widely, and recovery means rebuilding trust in the entire domain. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Active Directory is the central store of identities and passwords. An account in the highest groups (such as Domain Admins), or with directory replication rights, can read all password data from a domain controller, including the key that signs every Kerberos ticket. With these, access can be recreated even after passwords change. The compromise is usually a chain: a first login, a privilege step or two, then an admin credential. Root cause: weak links in the chain (see the linked findings) and administrative credentials exposed on ordinary machines.

#### Reproduction steps
1. State the starting position and list each earlier step as its own linked finding.
   Expected: The chain from first access to Domain Admin is clear and each step has evidence.
2. Show proof of domain admin level access harmlessly, for example by listing the members of the privileged groups or reading a non-sensitive file share on a domain controller.
   Expected: Output that shows the access level. Do not extract or keep real password data unless the rules allow it.
3. Record the time of each step and the accounts used.
   Expected: A timeline the client can compare with their logs.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Treat all domain accounts as exposed: reset passwords of privileged and service accounts, then reset the krbtgt password twice (with the replication gap between). Close the specific weaknesses used in the chain.
- **Longer term:** Use tiered administration, limit domain admin logons to domain controllers, deploy LAPS, monitor privileged group changes and replication requests, and rehearse domain recovery.
- **How to verify the fix:** Check that the weaknesses in the linked findings are fixed. Confirm the krbtgt password change date, the privileged group memberships, and that no unknown admin accounts exist.

#### Detection (for the client's defenders)
Look for directory replication requests from non-domain controllers (event 4662 with replication rights), new members in privileged groups (4728, 4732, 4756), privileged logons to unusual hosts (4624, 4672) and unexpected service installs on domain controllers (7045).

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
