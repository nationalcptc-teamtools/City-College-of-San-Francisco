*Draft, needs review.*

# 2. Weak, Default or Reused SSH and Administrator Passwords

- **Phase:** Initial access or credential validation
- **Risk:** 🟢 Safe / 🟡 Noisy / 🔴 Risky: banners, SSH configuration review and one login with a credential already found elsewhere are Safe; blank/default/password guessing is Noisy and requires the lockout check first; post-login changes or execution beyond approved enumeration are Risky and need approval every time
- **Tier:** Must know
- **Finding:** library L20 (`default-credentials`) for default passwords; no dedicated weak/reused Linux-password entry yet
- **Runs on:** SSH servers, Linux administrator accounts and service administration interfaces
- **Ports:** 22 (SSH) and product-specific administration ports
- **Tools:** nmap, nc, ssh-audit; an SSH client for one known-credential login after its command is approved

## What it is
SSH gives a remote command line. A weak or default administrator password lets anyone sign in; reuse means a credential recovered from a file, application, database or another host also works here.

Weak, default, exposed or reused credentials appeared in all six reviewed CPTC environments. Linux examples: weak root access, an exposed private SSH key, repeated administrator passwords, an unauthenticated privileged SSH path. Trace where a credential came from and validate it once; don't spray it everywhere.

**Checklist:** `checklists/15-linux.md` step 2 (Services: SSH and admin logins). If the credential is a domain credential, first review the lockout guidance in `checklists/10-ad-internal.md` step 2 (First credential). Identification commands come from Recon Field Guide Part 3 and Part 8 (`playbooks/recon/RECON-GUIDE.md`).

## Commands

1. Run the Linux-port check on one claimed host: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: TCP 22 and the other listed Linux-service ports are reported open, closed or filtered.
2. Read the SSH banner once: `nc -nv <host> 22` and press Ctrl-C after the banner — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: The server identifies its SSH implementation or closes without a banner.
3. Review offered SSH algorithms: `ssh-audit <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: The offered algorithms and version-related warnings are listed without a login.
4. Before trying a blank, default or guessed password, find and record the applicable lockout policy. Password guessing is 🟡 Noisy; stop if the threshold or observation window is unknown.
   Expected: A documented maximum number of attempts and window, or a decision not to guess.
5. A credential already recovered elsewhere may be checked with one login, which is 🟢 Safe. [[TODO: Add the exact single-login SSH validation command only after it appears in Recon Field Guide Part 3 or 8; it must perform one login and then disconnect.]]
   Expected: One success or failure, logged with the credential source and no repeated attempts.
6. [[TODO: Add any approved default-password check only after the lockout step and after the exact command/rating appear in the Recon Field Guide; no brute-force command belongs here.]]
   Expected: At most the approved number of attempts, with no account lockout.

## Evidence to capture
- `evidence/F-NNN-01.txt`: SSH banner and `ssh-audit` output with timestamp.
- `evidence/F-NNN-02.png`: one successful login showing the account and host, then immediate disconnect.
- The original source of the reused credential and the lockout-policy check; redact passwords and private-key material.

## Practice
- [[TODO: Choose an isolated SSH lab with one reused credential and one lockout policy, then verify the one-login procedure and stopping rule.]]
- Practise keeping default guessing, recovered-credential validation and password spraying as three separate activities with different evidence and risk.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
