### [[FINDING_ID]]: MSSQL Misconfiguration Allows Command Execution

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L09, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-mssql-misconfiguration.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs network access to the database port plus a login, which may come from a weak or default password, a reused login or another finding. Database servers are often reachable from many internal systems. Likely wherever database accounts have more rights than the application needs.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-250, ATT&CK T1505.001, https://learn.microsoft.com/en-us/sql/relational-databases/security/securing-sql-server

#### Summary
The database server is set up so a database login can run commands on the underlying Windows server, or has far more rights than needed. Someone with a database login can take over the server, and the database is often connected to other systems.

#### Business impact
Database servers hold the business's most valuable records. Taking over the server exposes that data and gives a base for attacking the rest of the network. Database service accounts are also often powerful in the domain. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
SQL Server has features that reach outside the database, such as xp_cmdshell, linked servers, and running programs or loading code. They are off by default but can be switched on by anyone in the sysadmin role, and some set-ups enable them or grant sysadmin to application logins. Other causes: the service runs as a highly privileged account, a weak sa password, mixed-mode authentication, and logins that can impersonate others or use linked servers with elevated rights. A database login then becomes operating-system access.

#### Reproduction steps
1. Identify the database server and its authentication mode, and confirm which login (provided or discovered) was used.
   Expected: A successful database login and the account's server roles.
2. Check whether the login holds the sysadmin role or can switch on external command features.
   Expected: The role list shows sysadmin, or the feature setting is on.
3. Only if the rules allow, run one harmless identity check to show which account the operating system sees.
   Expected: The service account name is returned. Record it and stop.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Remove sysadmin from application and user logins, switch off xp_cmdshell and other unused features, set a long random sa password (or disable sa), and run the SQL service under a low-privilege account.
- **Longer term:** Use least privilege for database logins, Windows authentication where possible, a managed service account for the service, separation of database servers from user networks, and regular review against a standard such as the CIS SQL Server benchmark.
- **How to verify the fix:** Run sp_configure and confirm xp_cmdshell is 0, check sysadmin members against an approved list, and confirm the service account in SQL Server Configuration Manager has no admin rights.

#### Detection (for the client's defenders)
Enable SQL Server audit and watch for sp_configure changes (event ID 15457 in the SQL error log), xp_cmdshell use, new logins or role changes, and child processes started by the SQL Server process.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
