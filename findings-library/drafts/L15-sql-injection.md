### [[FINDING_ID]]: SQL Injection in Web Application

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L15, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-sql-injection.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Anyone who can reach the web application can try it, often without logging in. Automated tools find the weakness quickly. One of the most common serious web flaws wherever queries are built from user input.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-89, ATT&CK T1190, https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html

#### Summary
The website passes what a visitor types straight into its database request. A visitor can craft input that changes the request to read, change or delete records, exposing customer and business data.

#### Business impact
Customer details, accounts and payment information may be read or altered, and stored logins taken. A breach could mean notification duties, loss of customer trust and fraud. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
When an application builds database queries by joining text, the database cannot tell the developer's instructions from the visitor's input, so specially shaped input becomes part of the query. Depending on the database and its permissions, this can allow reading other tables, bypassing login checks, changing data or, in some set-ups, running commands on the server. Root cause: untrusted input mixed with query code instead of passed separately as parameters.

#### Reproduction steps
1. Find an input that reaches the database (search box, login form, URL parameter, API field).
   Expected: The input works normally with expected values.
2. Send a harmless test input that breaks query syntax, such as a single quote, and compare the response with normal input.
   Expected: A database error, changed results or a delay shows the input is not handled safely.
3. Confirm with a safe read-only check and stop. Do not extract real customer data.
   Expected: Evidence that the query changed, for example a returned database version string.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Change the vulnerable queries to parameterized queries (prepared statements). Give the application's database account only the rights it needs.
- **Longer term:** Use parameterized queries or a trusted database library everywhere, validate input, test for injection in code review and automation, and add a web application firewall as an extra layer.
- **How to verify the fix:** Repeat the test input and confirm the response matches normal input, with no error or change. Review the code for string-built queries.

#### Detection (for the client's defenders)
Look in web server and database logs for requests with quotes, SQL keywords or odd characters in parameters, repeated database errors and unusually large responses.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
