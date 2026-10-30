### [[FINDING_ID]]: Outdated and Unsupported Software in Use

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L22, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-outdated-software.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Public vulnerability lists and ready-made exploits exist for most old versions, and version information is often visible to anyone scanning the host. Likelihood is high if the software is internet-facing or widely reachable.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-1104, ATT&CK T1190, https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/

#### Summary
Some systems run old software that the vendor no longer updates or that lacks important security fixes. Attackers keep lists of known flaws in these versions, so the systems are easy targets.

#### Business impact
Known flaws can give attackers full control of the system, risking data loss, downtime and use of the system to reach others. Unsupported software cannot be fixed by the vendor, so the risk grows with time. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Software releases get security fixes over time. Unpatched systems, or versions past end of support, keep publicly documented flaws open. Tools read version banners and match them against vulnerability databases. Root cause: no asset inventory and no patching or replacement process. A version number alone is not proof; confirm before rating high.

#### Reproduction steps
1. Identify the software and its version from banners, service information or the installed program list.
   Expected: Name and version noted.
2. Check the version against the vendor's support dates and public vulnerability lists.
   Expected: The version is past end of support or has known vulnerabilities.
3. Confirm the flaw applies in this configuration without running harmful code. Mark as Suspected if only the version was seen.
   Expected: Evidence of the version and a reference to the vulnerability entry.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Apply vendor security updates or upgrade to a supported version. Where it cannot be updated yet, limit network access to it and add monitoring.
- **Longer term:** Keep an inventory of all systems and software with support end dates, patch on a regular schedule, and scan for missing updates.
- **How to verify the fix:** Rescan after patching and confirm the new version and that the vulnerability no longer shows. Check the vendor support page.

#### Detection (for the client's defenders)
Use intrusion detection signatures for the known flaws, vulnerability scanner reports, and watch for unusual crashes or new processes on the affected host.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
