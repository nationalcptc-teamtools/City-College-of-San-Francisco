### [[FINDING_ID]]: Excessive Privileges Create a Path to Domain Admin

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L07, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-excessive-privilege-attack-path.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Use L07 for a privilege path that did NOT reach Domain Admin (or that we stopped short of). If the path reached Domain Admin, use L13 as the chain finding instead, rated Critical. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a foothold as a normal domain user, which is common after phishing or one weak password. Any user can read the account, group and computer relationships, so free tools find the path in minutes. Likely in large or older domains.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-269, ATT&CK T1069.002, https://learn.microsoft.com/en-us/windows-server/identity/ad-ds/plan/security-best-practices/best-practices-for-securing-active-directory

#### Summary
Ordinary accounts and groups hold more rights than they need. Linked together, these rights form a route from a low-level user up to higher privileges. We found the route but did not take it all the way to full domain control.

#### Business impact
Each step in the route is a place where a small foothold could grow into access to sensitive data and systems. Fixing the weakest links is cheap and removes the route before it can be used. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Active Directory is a graph of users, groups, computers and permissions. Over time, nested groups, leftover admin rights, privileged users' sessions on ordinary machines and delegated permissions create unintended paths. Every user can read this graph, so an attacker can map the shortest path to a high-value target. Root cause: privileges granted for convenience and never reviewed (no least privilege or tiering).

#### Reproduction steps
1. From a normal domain user, collect directory data on users, groups, computers, sessions and permissions.
   Expected: Data loaded into the analysis tool.
2. Map the shortest routes from the starting user to high-value groups such as Domain Admins.
   Expected: One or more routes listed, each with its steps.
3. Verify the weakest step only as far as the rules allow, and record what each step relies on.
   Expected: Evidence of the step. Stopping short of Domain Admin keeps this finding (use the domain compromise entry if it was reached).

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Remove the specific permissions, group memberships and admin sessions behind the weakest steps, and remove stale accounts from privileged groups.
- **Longer term:** Apply least privilege and administrative tiering (separate admin accounts for servers and workstations, no admin logons on ordinary machines), and review privileged groups and delegated permissions on a schedule.
- **How to verify the fix:** Repeat the path analysis after the changes; the route should be gone. Check Domain Admins, Enterprise Admins and Administrators membership against the approved list.

#### Detection (for the client's defenders)
Monitor privileged group changes (events 4728, 4732, 4756), admin logons to non-admin machines (4624, 4672), and large directory read bursts from one account.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
