*Draft, needs review.*

# 1. Database Without a Password or Using a Default Password

- **Phase:** Discovery (no credentials needed)
- **Risk:** 🟢 Safe / 🟡 Noisy / 🔴 Risky: specific-port identification and Redis `PING` are Safe; version probes and blank/default password attempts are Noisy; reading records, executing database features or changing data is Risky and needs approval every time
- **Tier:** Must know *(proposed)*
- **Finding:** library L20 (`default-credentials`)
- **Runs on:** MySQL/MariaDB, PostgreSQL, Redis and MongoDB servers
- **Ports:** 3306 (MySQL/MariaDB), 5432 (PostgreSQL), 6379 (Redis), 27017 (MongoDB)
- **Tools:** nmap, nc; database clients only after a reviewed procedure is approved

## What it is
A database should require a unique credential and restrict where connections come from. A blank password, a vendor default, PostgreSQL trust authentication or an unauthenticated Redis/MongoDB service lets anyone who can reach it connect.

One of the most repeated Linux-service weaknesses in the reviewed CPTC environments: missing, blank or default database authentication appeared in five of the six seasons. Examples: blank PostgreSQL superuser access, default MySQL billing credentials, passwordless MySQL/PostgreSQL administration, anonymous MongoDB.

**Checklist:** `checklists/15-linux.md` step 2 (Services: databases). Use Recon Field Guide Part 3 and Part 8 (`playbooks/recon/RECON-GUIDE.md`) for identification and library L20 (`default-credentials`) for reporting.

## Commands

1. Run the Linux-port check on one claimed host: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Each listed port, including the four database ports, is reported open, closed or filtered.
2. If an open database needs a version, probe only that port: `nmap -n -sV -p <port> <host>` — 🟡 Noisy. [[NOTE: from the Recon Field Guide]]
   Expected: A product/version banner is returned or the service remains unidentified.
3. For Redis only, connect once with `nc -nv <host> 6379`, type `PING`, then disconnect — 🟢 Safe. Run no other Redis command. [[NOTE: from the Recon Field Guide]]
   Expected: `+PONG` without authentication confirms unauthenticated Redis access.
4. Before any blank or default password attempt, find and record the applicable lockout or connection-control policy. Password guessing is 🟡 Noisy.
   Expected: The team knows the attempt limit and observation window, or stops because they are unknown.
5. [[TODO: Add one reviewed, product-specific authentication check for MySQL, PostgreSQL and MongoDB after that exact check and rating are added to Recon Field Guide Part 3 or 8; allow one blank/default attempt only and do not query records.]]
   Expected: Authentication succeeds or fails once, without reading or changing business data.
6. Stop after authentication proof. Reading tables, invoking operating-system features or changing records is 🔴 Risky and needs approval every time.
   Expected: The evidence proves missing/default authentication without accessing more data than necessary.

## Evidence to capture
- `evidence/F-NNN-01.txt`: port or version output with hostname, address and timestamp.
- `evidence/F-NNN-02.png`: the Redis `+PONG` or approved one-attempt authentication result.
- The lockout/control check and exact credential source; redact the password.
- Record whether access was observed, confirmed by one authentication attempt or only suspected from a banner.

## Practice
- [[TODO: Choose isolated MySQL, PostgreSQL, Redis and MongoDB training instances and verify that each retained check stops before reading or changing records.]]
- Practise explaining that an open port is not the finding; missing or default authentication is.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
