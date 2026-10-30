*Draft, needs review.*

# 6. Linux Privilege Escalation Misconfigurations

- **Phase:** Escalation (requires a low-privilege login)
- **Risk:** 🟢 Safe / 🔴 Risky: read-only enumeration of current privileges and permissions is Safe; invoking a privileged path, writing a cron-controlled file, using the Docker socket or obtaining root is Risky and needs approval every time
- **Tier:** Must know
- **Finding:** library L14 (`linux-privilege-escalation`)
- **Runs on:** Linux servers and appliances after a permitted low-privilege login
- **Ports:** not service-specific
- **Tools:** no approved on-host sudo/SUID/cron/Docker enumeration commands are in Recon Field Guide Part 3 or 8 yet

## What it is
Linux grants special power through sudo rules, SUID files, scheduled jobs and groups such as `docker`. A normal account can become root when one of these grants more authority than intended or trusts a file the user can change.

The reviewed CPTC reports contained Linux root compromise and privileged custom-service paths, but the specific sudo, SUID, writable-cron and Docker-group patterns were not prominent in the sample. It stays a core post-login topic: a low-privilege shell is common, and these checks decide whether it becomes full server control.

**Checklist:** `checklists/15-linux.md` step 3 (On the host). The current Recon Field Guide Part 3 (`playbooks/recon/RECON-GUIDE.md`) stops at network enumeration. Use library L14 (`linux-privilege-escalation`) for reporting.

## Commands

1. [[TODO: Add reviewed read-only enumeration commands for sudo rules, unusual SUID files, writable cron-controlled paths and Docker-group/socket access only after those exact commands and ratings are added to Recon Field Guide Part 3 or 8.]]
   Expected: A list of candidate privilege paths without invoking any of them.
2. Compare each candidate with the approved operating-system baseline and document why the current user can reach it.
   Expected: Each candidate is either dismissed or supported by permissions and configuration evidence.
3. Stop before invoking the path. Executing a privileged command, writing a cron file, starting a privileged container or obtaining root is 🔴 Risky and needs approval every time.
   Expected: Written approval defines one harmless proof and a stopping point, or the finding remains configuration-only.
4. [[TODO: Add a harmless, client-approved proof procedure for each class only after review; no shell, payload, file-write or container-escape command belongs in this draft.]]
   Expected: If approved, the minimum evidence shows elevated identity and immediately stops without persistence or changes.

## Evidence to capture
- `evidence/F-NNN-01.png`: the read-only rule, permission, group or scheduled-job evidence.
- The low-privilege starting identity, hostname and timestamp.
- Written approval for any escalation proof and a complete record of anything the approved procedure touches.
- Distinguish a candidate path from demonstrated root access.

## Practice
- [[TODO: Choose an isolated Linux privilege-escalation lab covering sudo, SUID, cron and Docker, then document the safe enumeration and separate approval-only proof for each.]]
- Practise writing L14 from configuration evidence even when escalation is not authorized.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
