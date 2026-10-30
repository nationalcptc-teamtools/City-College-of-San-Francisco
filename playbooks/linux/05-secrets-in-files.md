*Draft, needs review.*

# 5. Secrets in Files and Weak Key Permissions

- **Phase:** Authenticated enumeration or exposed-file review
- **Risk:** 🟢 Safe / 🔴 Risky: reading files already permitted to the current account and making one login with a recovered credential are Safe; changing permissions, replacing keys, executing scripts or using a secret to alter another system is Risky and needs approval every time
- **Tier:** Must know
- **Finding:** none in the library yet; use the finding that matches the exposed service or credential
- **Runs on:** Linux filesystems, application directories, home directories, backups, source/configuration trees and TLS directories
- **Ports:** not service-specific; initial access may come through SSH, FTP, NFS or a web application
- **Tools:** no approved on-host file-search command is in Recon Field Guide Part 3 or 8 yet

## What it is
Applications and administrators leave secrets in configuration files, private keys, shell history, readable backups and TLS key files. A password or key found this way may unlock a database, SSH host, admin interface or another environment.

Sensitive information, source/configuration exposure or hard-coded secrets appeared in all six reviewed CPTC environments. Examples: a private SSH key in source history, passwords in logs and text files, hard-coded application keys, exposed configuration, overly writable TLS material.

**Checklist:** for domain-authenticated shares, see `checklists/10-ad-internal.md` step 3 (Authenticated enumeration), which says to look for scripts, configs and backups. Linux checklist: `checklists/15-linux.md` step 3 (On the host). Initial service identification comes from Recon Field Guide Part 3 and Part 8 (`playbooks/recon/RECON-GUIDE.md`).

## Commands

1. Run the Linux-port check on one claimed host: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: FTP, SSH, RPC/NFS, rsync and the other listed Linux-service ports are reported open, closed or filtered.
2. [[TODO: Add reviewed read-only commands for current-user access to configuration files, private keys, shell history, backups and TLS key permissions only after those exact commands and ratings are added to Recon Field Guide Part 3 or 8.]]
   Expected: A minimal list of readable sensitive paths and permissions, without executing or modifying anything.
3. Validate one recovered credential with one login only; that is 🟢 Safe. [[TODO: Add the exact one-login validation command after it appears in the Recon Field Guide; do not spray the credential.]]
   Expected: One success or failure tied to the original file source.
4. Do not change permissions, replace a key, execute a discovered script or use the secret to change another system. Those actions are 🔴 Risky and need approval every time.
   Expected: Exposure and reuse are documented without altering the environment.

## Evidence to capture
- `evidence/F-NNN-01.png`: path, owner and permissions plus only the small redacted fragment needed to prove the secret.
- `evidence/F-NNN-02.png`: one approved credential-validation result, if performed.
- Hash evidence copies; record the original path, access identity and timestamp.
- Never place an unredacted private key, password or token in the public report repository.

## Practice
- [[TODO: Create an isolated filesystem exercise with configs, history, backups and TLS keys at both correct and incorrect permissions, then define the minimum evidence for each.]]
- Practise tracing one exposed secret to one safe login and stopping.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
