### [[FINDING_ID]]: Dangerous Active Directory ACL Allows Account Takeover

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L08, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-dangerous-ad-acl.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a foothold as an account that holds the permission or can reach it. These permissions are often inherited and forgotten, and any domain user can find them by reading the directory. Common in domains that have run for years.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-732, ATT&CK T1098, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/best-practices-for-securing-active-directory

#### Summary
Some accounts, groups or computers can change other, more powerful accounts (for example reset a password or add themselves to a group). An attacker who gets one of them can take over the stronger accounts, turning a small compromise into a large one.

#### Business impact
Taking over a privileged account can give access to company data, systems and settings, and lets an attacker blend in with legitimate admins. These permissions rarely show in normal user or group lists, so they go unnoticed. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Every Active Directory object has an access control list (ACL) saying who may do what. Rights such as GenericAll, WriteDACL, WriteOwner, ForceChangePassword or AddMember on a user, group or computer let the holder change that object. When low-privilege groups hold them, or they are inherited from a parent container, the holder can reset a password, edit group membership or change settings on a more powerful object. Root cause: delegation set too broadly and never audited.

#### Reproduction steps
1. As a domain user, read the permissions on directory objects (users, groups, computers, organizational units) and look for powerful rights held by non-admin accounts.
   Expected: Objects and the rights held by the starting account or its groups.
2. Rank the findings by what the target object controls (admin group, service account, domain root).
   Expected: The highest-value permission chosen for the finding.
3. Only if the rules allow, show the permission works with a reversible, agreed change on a test object, then undo it.
   Expected: The change is accepted, then reverted. Log both times.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Remove the dangerous permission from the account or group and check for inheritance from parent containers. Where the right is needed, scope it to the one object and action.
- **Longer term:** Review ACLs on privileged objects on a schedule, use tiered administration, use AdminSDHolder and protected groups for privileged accounts, and document every delegation.
- **How to verify the fix:** Re-read the ACL and confirm the account or group no longer has the right. Re-run the permission analysis and confirm the path is gone.

#### Detection (for the client's defenders)
Turn on directory service change auditing and watch for events 5136 (object changed) and 4662 (object access) on admin objects, plus password resets (4724) or group changes (4728, 4732) by unexpected accounts.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
