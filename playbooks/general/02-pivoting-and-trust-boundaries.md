*Draft, needs review.*

# 2. Pivoting and Trust Boundaries

- **Phase:** Movement and trust mapping
- **Risk:** 🟢 Safe to map routes and services, and one login with a known credential. Trying a credential or hash across a range of hosts (pass-the-hash) is 🟡 Noisy: many login attempts. Running commands on a client host (`evil-winrm`, `impacket-wmiexec`) or creating a tunnel, proxy or remote session is 🔴 Risky: ask the client contact in writing first, every time, and log it.
- **Tier:** Must know
- **Finding:** library L07 (`excessive-privilege-attack-path`); related L11 (`local-admin-password-reuse`) and L18 (`ot-network-segmentation`)
- **Runs on:** the tester workstation first; one agreed host at a time
- **Tools:** ip, nmap, NetExec
- **You need:** an in-scope foothold, route or recovered credential

## What it is
Pivoting means using access to one system to reach the next system or network. The pivot may be a network route, a trusted login, a shared administrator password or an application that can reach something we cannot.

Trust-boundary failures appeared in **all six reviewed CPTC environments**. The recurring path was simple: one exposed secret or foothold led to a privileged host, the credential or trust worked somewhere else, and the path ended at a business-critical system.

The first job is to draw that path. Do not build a tunnel just because the route exists. A clean map of source, destination, credential and business effect is evidence on its own.

**Checklist:** AD / Internal step 3 and step 4 (`checklists/10-ad-internal.md`). If the path crosses into control systems, stop and use OT / ICS: Before touching anything (`checklists/30-ot-ics-safe.md`).

## Commands

1. Record the tester workstation's current routes: `ip r` 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Each known network has a route and interface. An unexpected route is a lead, not permission to follow it.
2. On one claimed Windows host, identify the common Windows services: `nmap -n -sT -p 53,88,135,139,389,445,636,1433,3389,5985 <host>` 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Open ports show which trust or login checks might apply. This does not prove that a credential works.
3. On one claimed Linux host, identify the common Linux services: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Open ports show the next service to review. If the host might be OT, stop and use the OT checklist.
4. Check one recovered credential against **one agreed host** with one login only. 🟢 Safe. [[NOTE: from checklist 10]]
   Expected: One accepted login proves the trust link. One rejection is enough; do not guess or fan the credential across a range.
5. [[TODO: Write the exact tunnel, proxy or remote-session procedure, its stop conditions and cleanup. This is 🔴 Risky: ask the client contact in writing first, every time, and log it.]]
   Expected: Written approval names the source, destination, method and time window before anything runs.

## Evidence to capture

- `evidence/F-NNN-01.png`: the route or port evidence that shows the reachable boundary.
- `evidence/F-NNN-02.png`: one successful login or harmless landing page, with secrets redacted.
- A short path diagram: starting access → trust or reused credential → next system → business-critical target.
- The written approval and log entry before any tunnel, proxy or remote session.

## Practice

[[TODO: Select one free, public and legal lab that requires mapping a trust path across more than one host or network.]]

---
*Study draft for the CCSF 2026 team.*
