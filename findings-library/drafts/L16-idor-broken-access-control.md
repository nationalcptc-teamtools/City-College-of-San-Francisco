### [[FINDING_ID]]: Insecure Direct Object Reference Exposes Other Users' Data

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L16, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-idor-broken-access-control.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs only a normal account on the application (often free to create), then changing a number or ID in a request. No special tools. Common where the application checks login but not ownership.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-639, ATT&CK T1190, https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html

#### Summary
The application shows records based on an ID in the request but does not check that the record belongs to the person asking. A user can change the ID and see or alter other people's information, with no hacking tools.

#### Business impact
Other users' data, bookings, orders or account details may be exposed or changed. This creates privacy problems and can lead to fraud, complaints and legal duties. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
The application trusts an identifier supplied by the client (in a URL, form or API) to pick a record, and checks only that the user is logged in, not that the user may access that record. If IDs are sequential or guessable, anyone can step through them. This is broken access control, the top category of the OWASP Top 10. Root cause: no server-side authorization check on each object request.

#### Reproduction steps
1. Log in as one test user and note the ID used in a request for that user's own record.
   Expected: The user's own data is returned.
2. Change the ID to one belonging to a second test user you control, and repeat the request.
   Expected: The second user's data returned means the check is missing. A denied message means it works.
3. Test write actions only with your own test accounts. Do not view real customers' data.
   Expected: Evidence using only the test accounts.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Add a server-side check on every request that the logged-in user may access the specific record, and deny by default.
- **Longer term:** Do access-control checks in one shared place, use random non-guessable IDs as an extra layer (not the main control), and add automated access-control tests.
- **How to verify the fix:** Repeat the request with the other user's ID; the application should return access denied. Test each endpoint that takes an ID.

#### Detection (for the client's defenders)
Look for one account requesting many IDs in order, and requests for records not linked to the logged-in user. Application logs must record the user and the object.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
