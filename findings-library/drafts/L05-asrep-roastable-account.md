### [[FINDING_ID]]: Account Does Not Require Kerberos Pre-Authentication

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L05, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-asrep-roastable-account.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs network access to a domain controller and a list of user names (easy to guess or collect). No password is needed. Affected accounts are uncommon, usually left over from old applications or set by mistake.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-287, ATT&CK T1558.004, https://attack.mitre.org/techniques/T1558/004/

#### Summary
One or more accounts are set so the domain controller hands out login data without first checking that the requester knows the password. An attacker can guess the password offline. A weak password gives them that user's access.

#### Business impact
A successful guess gives an attacker a valid login with the account's permissions, a base for finding more access. The risk grows if the account is privileged or shared. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Normally Kerberos makes the user prove knowledge of the password before the domain controller replies (pre-authentication). With "Do not require Kerberos preauthentication" on, the domain controller replies to anyone, and the reply includes data encrypted with a key from the password. The attacker tests guesses offline with no lockouts and nothing logged on the client side. Root cause: an unneeded legacy setting combined with weak passwords.

#### Reproduction steps
1. With network access and a list of user names, ask the domain controller which accounts do not require pre-authentication.
   Expected: Affected accounts return data; others return an error that pre-authentication is required.
2. Save the returned data for each affected account to the evidence folder.
   Expected: One entry per affected account.
3. Test password strength offline against an agreed wordlist within the engagement's limits.
   Expected: A recovered password (first and last characters only) or no result.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Clear "Do not require Kerberos preauthentication" on every account that has it, and reset those accounts' passwords to long random values.
- **Longer term:** Audit this setting on a schedule (it is easy to query), enforce a strong password policy, and use a long random password for any account that must keep the setting.
- **How to verify the fix:** Query the directory for accounts with the DONT_REQ_PREAUTH flag; the result should be empty. Repeat the request from the test machine and confirm every account now requires pre-authentication.

#### Detection (for the client's defenders)
Look for Kerberos authentication requests (event 4768) with pre-authentication type 0, and many requests for different user names from one source.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
