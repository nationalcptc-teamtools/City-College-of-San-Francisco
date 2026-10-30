### [[FINDING_ID]]: Default Credentials on Administrative Interface

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L20, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-default-credentials.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Default logins are published in manuals and online lists, so anyone who finds the interface can try them, and network scans find these interfaces easily. Very common on appliances, cameras, printers and web consoles.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-1392, ATT&CK T1078.001, https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/

#### Summary
An administrative page still accepts the user name and password it shipped with. Anyone who finds it and looks up the default can log in as an administrator and control the device or application.

#### Business impact
Administrator access can let an attacker read or change settings and data, use the device to reach other systems, and disrupt services. It needs no skill, so it is often the first thing attackers try. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Vendors set a standard login on new products so they can be set up. If nobody changes it at installation, it stays the same on every unit and is publicly known. Root cause: no process to change default credentials at deployment and no check for them afterward.

#### Reproduction steps
1. Identify the administrative interface and the product name or version from the login page.
   Expected: Product identified.
2. Look up the vendor's documented default login and try it once or twice, within the rules of engagement.
   Expected: Login succeeds or fails. Success confirms the finding.
3. Record what the account can access without changing any setting.
   Expected: A screenshot of the logged-in page with sensitive values hidden.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Change the default password and, where possible, rename or disable the default account. Restrict the interface to a management network.
- **Longer term:** Add a deployment checklist that requires changing default credentials, keep a device inventory, scan regularly for default logins, and use a password manager or central login (SSO).
- **How to verify the fix:** Try the default login again; it should fail. Confirm the new credentials are unique and stored in the password manager.

#### Detection (for the client's defenders)
Watch for successful logins to admin interfaces from unusual sources and configuration changes soon after. Device and web-server logs show login events.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
