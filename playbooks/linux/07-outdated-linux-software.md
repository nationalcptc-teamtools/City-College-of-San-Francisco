*Draft, needs review.*

# 7. Outdated Software with Known Vulnerabilities

- **Phase:** Discovery and version verification
- **Risk:** 🟢 Safe / 🟡 Noisy / 🔴 Risky: single banners and SSH algorithm review are Safe; version probes are Noisy; exploit validation, payload execution or any state change is Risky and needs approval every time
- **Tier:** Must know
- **Finding:** library L22 (`outdated-software`)
- **Runs on:** Linux operating systems, SSH, databases, web/application servers and network services
- **Ports:** any exposed service port
- **Tools:** nc, ssh-audit, nmap; vendor advisories and public vulnerability records for offline verification

## What it is
Old software may lack security fixes or vendor support. The version is a lead, not proof: distributions sometimes backport fixes without changing the version string a scanner expects.

Outdated or unsupported components appeared in all six reviewed CPTC environments. Linux examples across several seasons: old Apache/Tomcat, OpenSSH, MariaDB and TLS components. The finding should name the exact version and the vulnerability or support deadline that applies.

**Checklist:** for web-facing software, see `checklists/20-web-app.md` (Map it), which requires exact stack/version fingerprinting before checking known CVEs. Linux checklist: `checklists/15-linux.md` steps 1 (Discovery) and 4 (Outdated software). Use Recon Field Guide Part 3 and Part 8 (`playbooks/recon/RECON-GUIDE.md`) and library L22 (`outdated-software`).

## Commands

1. Identify common Linux services on one claimed host: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Candidate service ports are listed.
2. For SSH, read the banner once with `nc -nv <host> 22`, then press Ctrl-C — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: An SSH implementation/version banner or a closed connection.
3. Review SSH algorithms and version warnings with `ssh-audit <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Offered algorithms and warnings are listed without authentication.
4. Probe only one confirmed open service port for a version: `nmap -n -sV -p <port> <host>` — 🟡 Noisy. [[NOTE: from the Recon Field Guide]]
   Expected: The service/version is identified or remains unknown.
5. Check the exact version offline against the vendor's support information and vulnerability records; account for distribution backports.
   Expected: A primary reference showing end of support or that the specific configuration remains affected.
6. [[TODO: Add any non-destructive product-specific vulnerability check only after the exact command and rating are added to Recon Field Guide Part 3 or 8; exploitation or payload execution is 🔴 Risky and needs approval every time.]]
   Expected: Applicability is confirmed without executing the vulnerability, or the status remains Suspected.

## Evidence to capture
- `evidence/F-NNN-01.txt`: exact banner/version and timestamp.
- `evidence/F-NNN-02.png`: vendor support or vulnerability reference showing affected versions and conditions.
- Distribution/package context needed to rule in or rule out a backported fix.
- Label version-only evidence as Suspected rather than claiming exploitation.

## Practice
- [[TODO: Choose supported and intentionally outdated Linux services, then practise distinguishing an affected build from a backported fix.]]
- Practise writing L22 without overstating a banner as proof of exploitability.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
