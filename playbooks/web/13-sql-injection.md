*Draft: command steps not filled in yet.*

# 13. SQL Injection

- **Phase:** No credentials or Low credentials (wherever the input is)
- **Risk:** 🟡 Noisy: detection and reading data send many odd requests. **Any test that could change or delete data is 🔴 Risky:** approval every time. Keep automated tools at their lowest risk setting.
- **Tier:** Must know
- **Finding:** library L15 (`sql-injection`)
- **Ports:** 80, 443
- **Tools:** Burp Suite, sqlmap
- **You need:** an input that reaches the database (search boxes, IDs in URLs, logins)

## What it is
The app pastes user input straight into a database query. Crafted input changes the query, so an attacker can read, add, change or delete data, and sometimes run commands on the server.

In 2024 a search page returned a verbose database error, which showed where the input landed; an automated tool then read the users table.

**Fix to recommend:** parameterized queries (prepared statements) everywhere. The 2024 doc lists the call for each language; keep that list.

## Commands
- **Fuzzing:** using something like `wfuzz` for bruteforcing.

- **sqlmap** - Using sqlmap the assessor extracted the user's table from the public database with the payload, example:
`';select * from users`


## Evidence to capture
- `evidence/F-NNN-01.png`: the error or changed response that shows the injection.
- `evidence/F-NNN-02.png`: proof of data access (table names, or one row with values redacted).
- The logged commands with timestamps.

## Practice
- PortSwigger Web Security Academy, SQL injection labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
