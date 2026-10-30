### [[FINDING_ID]]: Shared Local Administrator Password Enables Lateral Movement

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L11, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-local-admin-password-reuse.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs administrator access on one machine in the group, which an attacker may get through other findings. Reuse then makes success likely on every machine with the same password. Common where machines are built from one image.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-262, ATT&CK T1550.002, https://learn.microsoft.com/en-us/windows-server/identity/laps/laps-overview

#### Summary
Many computers share the same built-in administrator password. An attacker who learns it from one machine can sign in to all the others, so one machine's weakness becomes the whole group's.

#### Business impact
Gaining one machine can quickly become control over many workstations and servers, their data and other users' logins. Clean-up is costly because every machine is affected. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
When machines are cloned from one image or built by a script, the local administrator account often gets the same password everywhere. The password hash can be used directly to sign in elsewhere (pass-the-hash) without cracking it. Domain policy does not cover local accounts, so nothing forces the password to be unique or to change. Root cause: no system giving each machine its own random local admin password.

#### Reproduction steps
1. With local administrator rights on one machine, obtain the local administrator credential or its hash as allowed by the rules of engagement.
   Expected: A credential value is recovered (redact in evidence).
2. On a small agreed sample of other machines, check whether the same credential is accepted for the local administrator account.
   Expected: Accepted on several hosts. Record only which hosts.
3. Stop after proving reuse; do not move further without client approval.
   Expected: List of hosts where reuse was shown.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Set a unique random password on every local administrator account now, and disable the built-in administrator account where it is not needed.
- **Longer term:** Deploy Windows LAPS (Local Administrator Password Solution) so each machine's local admin password is random, rotated and stored in the directory with access limited to admins. Block local-account network logons with the "Deny access to this computer from the network" policy.
- **How to verify the fix:** Confirm LAPS is applied (password attribute populated, expiry current). Test that the old shared password no longer works on any machine.

#### Detection (for the client's defenders)
Watch for network logons (event 4624, logon type 3) by the local Administrator account from one source to many hosts, and NTLM use for local accounts.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
