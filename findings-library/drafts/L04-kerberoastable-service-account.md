### [[FINDING_ID]]: Kerberoastable Service Account with Crackable Password

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L04, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-kerberoastable-service-account.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Any valid domain account can start this, even a low-privilege one, so one phished or guessed login is enough. The requests look like normal Kerberos traffic. Success depends on whether the service account's password is weak. Common where old service accounts exist.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-521, ATT&CK T1558.003, https://learn.microsoft.com/en-us/windows-server/security/group-managed-service-accounts/group-managed-service-accounts-overview

#### Summary
Some service accounts have passwords that can be guessed offline. Any logged-in domain user can request the data needed, without triggering a lockout. If the password is weak, the attacker gains that service's access, which is often high.

#### Business impact
Service accounts often run databases and business applications and tend to have broad rights. Taking one over can expose business data and give a route to administrator access. Because the guessing happens offline, the client's systems may show nothing. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Kerberos lets any domain user request a service ticket for any account with a service principal name (SPN). Part of the ticket is encrypted with a key derived from the service account's password. The attacker saves the ticket and tries guesses on their own computer, fast and with no lockouts. Root causes: human-chosen passwords on service accounts, passwords that never change, excess rights, and older RC4 encryption being allowed.

#### Reproduction steps
1. From any valid domain account, list the accounts that have a service principal name.
   Expected: A list of user accounts with SPNs. Note which are in privileged groups.
2. Request service tickets for those accounts and save them to the evidence folder.
   Expected: Ticket data returned for each account, no error.
3. Test password strength offline against an agreed wordlist, within the engagement time limit.
   Expected: A recovered password (first and last characters only) or no result. An uncracked ticket still shows the exposure.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Set long random passwords (25 or more characters) on every account with an SPN. Remove SPNs from accounts that do not need them and remove excess group memberships (especially Domain Admins).
- **Longer term:** Move services to group Managed Service Accounts (gMSA), which rotate passwords automatically. Require AES for Kerberos on service accounts and monitor ticket requests.
- **How to verify the fix:** List accounts with an SPN again and confirm each uses a gMSA or a recently changed password of 25+ characters. Re-run the offline test with the same wordlist; it should fail.

#### Detection (for the client's defenders)
Look for Kerberos service ticket requests (event 4769) using RC4 encryption (type 0x17), and one account requesting tickets for many services in a short time.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
