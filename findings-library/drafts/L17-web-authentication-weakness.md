### [[FINDING_ID]]: Weak Web Application Authentication Controls

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L17, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-web-authentication-weakness.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Anyone who can reach the login page can try. Guessing, reuse of leaked passwords and missing rate limits are all low-skill. Likely for public-facing applications.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-287, ATT&CK T1110, https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html

#### Summary
The website's login does too little to stop guessing or misuse of accounts: no limit on attempts, weak password rules, no second step, or sessions that never end. An attacker can reach accounts with little effort.

#### Business impact
Taking over a customer or staff account exposes that user's personal data and functions, and an admin account can expose the whole application. This can damage trust and cause fraud. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Weak authentication includes no lockout or rate limit, error messages that reveal whether a user name exists, weak password rules, no multi-factor authentication, predictable or long-lived session tokens, password resets with guessable answers, and sessions that survive logout. Each makes a login easier to guess, steal or reuse. Root cause: login features built without the standard protections.

#### Reproduction steps
1. Test how the login responds to a wrong user name and to a wrong password for a real user.
   Expected: Different messages reveal which user names exist.
2. Send a small, agreed number of wrong attempts for a test account and watch for lockout, delay or rate limiting.
   Expected: No lockout or delay after repeated failures supports the finding.
3. With test accounts, check whether sessions end on logout and whether the password reset is safe.
   Expected: A session still works after logout, or the reset is guessable.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Add rate limiting and temporary lockout on login, use identical messages for wrong user name and wrong password, enforce a stronger password rule, and end sessions on logout.
- **Longer term:** Require multi-factor authentication, use a tested login framework instead of custom code, set short session lifetimes and monitor failed logins.
- **How to verify the fix:** Repeat the attempts and confirm lockout or delay, the same error text for both cases, and that the old session is rejected after logout.

#### Detection (for the client's defenders)
Alert on many failed logins per account or source, logins from new places and password reset bursts.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
