### [[FINDING_ID]]: Vulnerable AD CS Certificate Template Allows Privilege Escalation

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L12, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-adcs-vulnerable-template.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Critical [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a valid domain account (often any user, sometimes a computer account) and network access to the certificate authority. Unsafe templates exist in many domains because they were created for convenience. Once found, using them is quick and quiet.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-295, ATT&CK T1649, https://posts.specterops.io/certified-pre-owned-d95910965cd2

#### Summary
The certificate system is set up so an ordinary user can get a certificate identifying them as someone more powerful, such as an administrator. Certificates work like passwords for the domain, so the attacker can sign in as that user.

#### Business impact
This can lead to complete takeover of the domain from a normal account. Certificates are valid for a year or more, so access can outlast a password reset. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Active Directory Certificate Services (AD CS) issues certificates that prove identity. Templates decide who may request a certificate, what it can be used for, and who the subject is. Risky settings include letting the requester name any identity ("enrollee supplies subject"), letting low-privilege groups enrol for client authentication certificates, weak approval rules, and dangerous permissions on the template or the certificate authority itself. A certificate with the right use can be exchanged for a Kerberos login, so an unsafe template becomes a route to any account. Root cause: templates created or left with overly broad enrolment rights and settings.

#### Reproduction steps
1. As a domain user, list the certificate authorities and templates and the enrolment permissions on each.
   Expected: Templates with who may enrol.
2. Flag templates that allow client authentication, let the requester supply the subject, or are enrollable by broad groups such as Domain Users.
   Expected: One or more templates flagged by the checking tool.
3. Only if the rules of engagement allow it, request a certificate for a low-risk test identity to prove the issue, then report without going further.
   Expected: A certificate is issued for the chosen identity. Record the time and request ID for the client to revoke.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Disable or unpublish the flagged template, or remove the risky setting (turn off "Supply in the request") and broad enrolment rights. Require CA manager approval where the use is needed. Revoke any certificate issued during testing.
- **Longer term:** Review all templates and CA permissions with an AD CS auditing tool on a schedule, apply Microsoft's AD CS patches, keep the CA and its keys on a protected tier, and monitor certificate requests.
- **How to verify the fix:** Re-run the AD CS template check and confirm the template is no longer flagged. Request a certificate as a normal user; it should be refused or need approval.

#### Detection (for the client's defenders)
Enable CA auditing and watch for certificate requests and issuance (events 4886, 4887) where the requester differs from the named subject, template changes (4898, 5136), and certificate-based sign-ins (4768 with certificate information).

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
