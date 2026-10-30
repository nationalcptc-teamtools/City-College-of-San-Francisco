### [[FINDING_ID]]: Local Privilege Escalation via Sudo/SUID Misconfiguration

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L14, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-linux-privilege-escalation.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a low-privilege shell on the Linux host, which other findings (weak passwords, web flaws) often provide. The misconfigurations are easy to spot from there. Common on servers where convenience rules were added over time.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-250, ATT&CK T1548.003, https://attack.mitre.org/techniques/T1548/003/

#### Summary
A normal user on a Linux server can run certain programs with full administrator (root) rights because of how sudo or special file permissions are set. A small foothold becomes full control of that server.

#### Business impact
Root access means access to all the server's data, stored passwords and connections to other systems. It also lets an attacker hide their activity and stay in place. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Sudo lets chosen users run chosen commands as root, and SUID files run with their owner's rights. Problems arise when sudo rules allow commands that can start a shell or edit files, allow any command with no password, or use wildcards, or when SUID is set on programs never meant to hold it. Many everyday programs can be used to escape into a root shell once they run with elevated rights. Root cause: privilege granted to programs without checking what else they can do.

#### Reproduction steps
1. From a low-privilege account on the host, list what the account may run with sudo.
   Expected: A list of allowed commands. Entries such as ALL or NOPASSWD are of interest.
2. List files with the SUID permission and compare them with the usual set for the operating system.
   Expected: Unusual SUID programs listed.
3. Only if the rules allow, show that one allowed program gives root by running a harmless identity check afterward.
   Expected: Output shows the root user. Record and stop.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Remove broad sudo rules (ALL, NOPASSWD, wildcards) and limit users to named commands that cannot start a shell. Remove the SUID bit from programs that do not need it.
- **Longer term:** Apply least privilege in sudoers, keep sudoers files under configuration management and review, log sudo use centrally, and keep the operating system patched.
- **How to verify the fix:** Run sudo -l as the test user and confirm only intended commands appear. Re-list SUID files and compare with the approved list.

#### Detection (for the client's defenders)
Check the authentication log for sudo use (command and user), file integrity alerts on sudoers, and new root-owned processes started by ordinary users.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
