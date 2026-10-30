### [[FINDING_ID]]: Weak Domain Password Policy Permits Password Spraying

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L06, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-weak-password-policy.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Anyone with network access to a login service (domain controller, VPN, email, web portal) can try it. Weak policy plus common passwords makes success likely across a few hundred accounts. One of the most common ways attackers get a first login.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-521, ATT&CK T1110.003, https://pages.nist.gov/800-63-3/sp800-63b.html

#### Summary
The domain allows short, simple passwords and does not lock accounts after repeated wrong guesses. An attacker can try a few common passwords across every user and is likely to find one that works, with no special tools.

#### Business impact
One staff login can be enough to read email, reach internal systems or start more serious attacks. Weak passwords also turn other findings, such as service account or hash capture issues, into real breaches. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Password spraying tries a few common passwords (such as a season and year) against many accounts, staying below the lockout threshold. It works because of a low minimum length, no block on common or breached passwords, a missing or very high lockout threshold, and reused or never-expiring passwords. Root cause: a policy that relies on users choosing hard passwords without checking that they did.

#### Reproduction steps
1. As any domain user, read the domain password policy and note the minimum length, lockout threshold and observation window.
   Expected: Policy values shown. Short length or a lockout of 0 supports the finding.
2. Check that the account list is reachable (see the anonymous access entry) and agree with the client how many accounts and attempts are allowed.
   Expected: An approved, small number of attempts per account.
3. Only if the rules of engagement allow it, try one agreed common password across the account list, below the lockout threshold.
   Expected: A count of accounts that accepted it. Record counts, not real users' passwords.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Set minimum password length to at least 12 characters (14 for admins), set an account lockout threshold (for example 5 failed attempts), and block known-weak passwords with a banned-password list.
- **Longer term:** Use passphrases, multi-factor authentication on remote and email access, and fine-grained password policies for privileged and service accounts. Follow NIST guidance: favour length over complexity rules and check new passwords against breach lists.
- **How to verify the fix:** Run Get-ADDefaultDomainPasswordPolicy and confirm length, lockout threshold and observation window. Set a banned password on a test account; it should be refused.

#### Detection (for the client's defenders)
Look for many failed logons (event 4625, or 4771 for Kerberos) across many accounts from one source, and clusters of lockouts (event 4740).

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
