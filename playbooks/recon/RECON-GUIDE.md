# Recon Field Guide

Recon and enumeration for the Windows, Linux and Web lanes, from first host discovery to full enumeration. Stops before exploitation.

> **Scope beats everything.** Rulebook p4: teams may only act against the target infrastructure "in accordance with the Scope of Work (SOW)", and unapproved activity "includes port scans, unauthorized connection attempts, vulnerability scans, etc." Penalties run up to disqualification. Every target comes from `scope.txt`. Broad scans use `-iL`. A single-host command runs only after `grep` shows the host is in `scope.txt` (1.2). Every command carries a safety rating.

**How to use this guide**

- **Everyone** - shared core
- **By Role**:
   - Part 2 - Windows/AD
   - Part 3 - Linux
   - Part 4 - Web
   - Part 5 - Report Writers
- **Part 6 (masscan, rustscan)** - first get comfortable with everything in Part 1.
- **Part 7** - team workflow: who scans what.
- **Part 8** - cheat sheets, can be printed.
- **Flags**:
   - nmap - 1.6
   - Windows tools - 2.2
   - Linux tools - 3.2
   - web tools - 4.1 
   - masscan, rustscan - Part 6

Sources: 
- Official rulebook https://cp.tc/docs/cptc-rules.pdf
- Our team rules in `CONVENTIONS.md` (R2, R3, R5, R6, R7, R10, R11, R12, R17), and the run sheets in `checklists/`.

---

## Contents

1. [Part 1: Shared core](#part-1-shared-core)
2. [Part 2: Windows / Active Directory](#part-2-windows--active-directory)
3. [Part 3: Linux](#part-3-linux)
4. [Part 4: Web applications](#part-4-web-applications)
5. [Part 5: For the report writers](#part-5-for-the-report-writers)
6. [Part 6: Advanced (locked): masscan and rustscan](#part-6-advanced-locked-masscan-and-rustscan)
7. [Part 7: Team recon workflow](#part-7-team-recon-workflow)
8. [Part 8: Cheat sheets](#part-8-cheat-sheets)
9. [Glossary](#glossary)

---

# Part 1: Shared core

## 1.1 The safety ratings

Every command and flag has a rating, the same key as `playbooks/README.md` (team repo) and the checklists.

| Rating | Meaning | Before running it |
|---|---|---|
| 🟢 **Safe** | Few packets, read-only, normal-looking traffic. A single login with valid credentials is Safe. Fine against any in-scope IT host. | Check the target is in scope. Run it. |
| 🟡 **Noisy** | Many packets or connections, or guesses at something (names, community strings, paths, blank or null-session logins). Rarely breaks a healthy server, but can slow one down and fills the client's logs. | Announce it to the team: "full port scan on .15". Never against OT hosts. |
| 🔴 **Risky** | Can crash a service, lock an account, change data, or reach something outside scope. | Stop. Get approval from the Team Captains, Client, or Operations, log who said yes and when, then run it. |
| **Prohibited** | Forbidden by the RoE. No symbol; no command in this guide is rated for use. | Never run it. |

**Ratings apply to both the command and the target.** 

⚠️ **The same `nmap -sV` is**
- 🟢 against a web server
- 🔴 against a ride controller.

A rating like "🟡, 🔴 on OT" means 🟡 on IT hosts and 🔴 on OT hosts.


⚠️ **Flags move the rating.**
   - The step tables (1.7, 2.3, 3.3, 4.2) show this in the "Why, and what raises it" column.
   - Flag tables rate the flag only; the target can still raise it.


🌟 **APPROVALS** - Log each approval in your Field Notes > Approvals`~/cptc-work/field-notes/<yourname>/NOTE-approvals.md` (`NOTE-approvals.md` below):

```
14:05 nikto on 10.0.5.20:80, approved by Operations (see email: "Request for OT Engagement)
```

## 1.2 Scope: what we may touch

**Scope of Work (SOW):**
- The list of targets we are approved to test (IP ranges, hosts, URLs) and what is off limits
**Rules of Engagement (ROE):** how we may test.

**What is NEVER a target:** 
- Other teams, the Operations Team, supporting infrastructure, monitoring and management systems, software agents on competition hosts, hosting institutions, and public Internet resources.

**Clarifications and Approvals:**
- If unsure whether a target is acceptable, "contact the Operations Team before engaging those targets" (team rule R12).

**Scope files:**

At kickoff, before any scan, build these plain text files in `~/cptc-work/` from the SOW, one entry per line (`scope-web.txt` only if the SOW names URLs, `ot-ranges.txt` only if OT is suspected):

| File | Holds | Used with |
|---|---|---|
| `scope.txt` | Every in-scope range and host, copied from the SOW | `-iL scope.txt` |
| `exclude.txt` | Every host or range the SOW excludes, plus every OT host found | `--excludefile exclude.txt` |
| `scope-web.txt` | Web addresses (URLs) the SOW names, if any, for the Web lane | `httpx-toolkit -l scope-web.txt` (Part 4) |
| `ot-ranges.txt` | Suspected OT ranges, a subset of `scope.txt` | `-iL ot-ranges.txt` (1.12, step 5) |

`scope.txt` and `exclude.txt` hold **IP addresses, ranges (CIDR) and hostnames only**, one per line. nmap's `-iL` does not accept URLs, and masscan accepts neither URLs nor hostnames (IPs and ranges only). Put URLs in `scope-web.txt`.

**`exclude.txt` is the one skip list**, for the guide and the checklists. Append every new OT host to it with a tag, for example `10.0.5.20  # OT` (nmap ignores `#` comments; check on our Kali image). To list only the OT hosts: `grep '# OT' exclude.txt` 🟢. Each person keeps their own copy until shared storage is decided.

Two checks before the first scan:

1. Read `scope.txt` against the SOW line by line. A CIDR typo (`/16` for `/24`) scans 65,000 hosts by accident.
2. Preview the target list: `nmap -sL -n -iL scope.txt --excludefile exclude.txt` 🟢.
It only lists targets; `-n` stops reverse lookups. Hostnames in `scope.txt` are still resolved through our DNS server, so nothing goes to the targets but DNS queries can. Prefer IP addresses in `scope.txt`; if it holds hostnames, check the DNS server (1.9) is in scope. The count at the end should match the SOW.

**Never type a target by hand.** Use `-iL scope.txt`. Before a single-host command on a host you claimed, check it is in scope:

- If `scope.txt` lists single addresses: `grep -Fw 10.0.5.20 scope.txt`. `-F` treats the address as plain text (otherwise the dots match any character); `-w` matches the whole address, so `10.0.5.2` does not match `10.0.5.20`.
- If it holds ranges (CIDRs), let nmap expand them: `nmap -sL -n -iL scope.txt --excludefile exclude.txt | grep -Fw 'for 10.0.5.20'` 🟢. Each target prints as `Nmap scan report for 10.0.5.20`, so the grep finds the host only if it is in scope and not in `exclude.txt`. Nothing is sent to the targets.

If the grep prints nothing, the host is out of scope: stop and ask Operations.

> **Where target addresses come from**
>
> | File | What it holds | Who writes it | Used for |
> |---|---|---|---|
> | `scope.txt` | Everything we can touch, from the SOW | Built once at kickoff | Discovery only |
> | `live.txt` | Hosts that answered discovery | nmap | Port scans, and picking hosts to claim |
> | `<claimed-hosts>` (defined in 1.7) | The hosts you claimed | You, copied line by line from `live.txt` | Your deeper scans |
> | `hosts.csv` | The team tracker: <br>one row per host (owner, OS, ports, stage) | The team | Tracking only. It is not a target list for tools. |
>
> For one host:
>
> 1. See it in `live.txt` or `hosts.csv` and claim it (Part 7).
> 2. Copy and paste the address into your claimed-hosts file or the command. Never retype it.
> 3. Run the scope check above before a deep scan.
>
> Addresses come from files that came from the SOW, never from memory or typing.

**Tool defaults can leave scope.** Anything that follows links, redirects or DNS names can wander off target: crawlers following links to another site, a hostname that resolves outside scope, tools that fetch updates or look things up on the Internet. When a tool reports an address you did not give it, stop and check the SOW.

## 1.3 Stop rules

**Stop and tell the team** if anything goes down, an account locks, an unexpected host appears, or a sensitive system responds. Then:

1. Stop the command (`Ctrl-C`) or other action. Don't rerun it just to check.
2. Tell the team and write the time and command in your notes.
3. If critical enough: Tell Operations or the Client. Write an incident report (`templates/incident-report.md`). Include what occurred (source and destination IPs, timeline, impact/damage), what was affected, and a remediation plan. A thorough, timely report may reduce the penalty. Incomplete, vague, or late reports cause further point loss.

## 1.4 OT and brittle systems

Operational technology (ride controllers, building automation, industrial devices) may be in play.

**Scope depends on the SOW and ROE:** (`checklists/30-ot-ics-safe.md`. 

History: CCSF team found a real system in service (a tram), asked the client first, successfully engaged the system, and were credited for starting and stopping it with a simple request.

**Pattern: find it, identify it, then ask.**

- **Finding** OT is a 🟡 slow, narrow pass (see 1.12, step 5).
- **Identifying** an OT host is read-only and one host at a time (`checklists/30-ot-ics-safe.md`).
- **Anything past identifying** (reading values, sending a command, a write) is 🔴. Ask the client contact in writing first, every time, and log the answer (R11).
- **No aggressive scans on OT.** Rulebook p10: actions that interrupt the environment cost points.
- Discovered OT host goes on the whiteboard and into `exclude.txt` tagged `# OT`. **All broad scans after that skip it.**

History: a past team's aggressive vuln scan on an industrial subnet disrupted simulated operations and kept running until someone noticed. Other teams asked the client before some vulnerability tests. One got approval before an EternalBlue test and reported no harm; the same team later ran an unapproved test that disrupted the domain.

Lesson: gentle discovery, then ask.


## 1.5 Ports: where they go in a command

```
nmap [scan type] [options] -p <ports> <targets>
```

| You want | Write | Notes |
|---|---|---|
| One port | `-p 443` | |
| A list | `-p 22,80,443` | No spaces |
| A range | `-p 1-1024` | Inclusive |
| Everything | `-p-` | Same as `-p 1-65535`. 🟡 on IT hosts. |
| Most common N# | `--top-ports 100` | Ranked by how often ports are open. Use instead of `-p`. |
| TCP and UDP together | `sudo nmap -n -sS -sU -p T:80,U:161 <host>` | `-sS` = TCP SYN scan, `-sU` = UDP scan (both explained in 1.6). `T:` and `U:` prefixes pick which ports go with which protocol. Needs both scan flags. |
| Skip ports | `--exclude-ports 502,102` | Never scanned, even inside a range |
| Fast preset | `-F` | Top 100 ports. Same as `--top-ports 100`. |

Default with no port option: the top 1000 TCP ports. Docs: https://nmap.org/book/port-scanning-options.html

**Port ranges by default risk**

| Range or port | Default rating | Why |
|---|---|---|
| Standard IT services: <br> 21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 389, 443, 445, 993, 995, 1433, 3306, 3389, 5432, 5985, 8080, 8443 | 🟢 | Built for many clients; a connect or SYN check is normal traffic |
| Well-known ports: <br> 1-1023 in general, except the OT ports in the last row | 🟢 | Standard services; safe to probe at a polite rate |
| High ports 1024-65535 (`-p-`) | 🟡 | Mostly empty, but many probes, and odd services listen here |
| Printers: 515, 631, 9100 | 🟡 | Some printers print junk or hang when a scan connects to 9100 |
| UDP (any `-sU`) | 🟡 | Slow, retries a lot; UDP services like SNMP are fine, others may react oddly |
| OT/ICS ports (list in `checklists/30-ot-ics-safe.md`, for example 102, 502, 2404, 4840, 20000, 44818, and 47808/UDP) | 🔴 for broad scans | Many controllers fall over on unexpected data or version probes. Only the slow pass in 1.12 touches these. |

**OT exclusion** On any range that might hold OT, add `--exclude-ports <OT-string>` to every scan from ladder step 5 to step 11 (R11). Steps 8, 9 and 11 (they name the open ports of one host) also run only after the host is cleared as not OT. `<OT-string>` is the full string in `checklists/30-ot-ics-safe.md`:

```
T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

Where a checklist and this guide differ, the stricter condition applies and both files are fixed to match in the next review.

## 1.6 nmap flag reference

Every nmap flag in this guide, grouped by purpose. Ratings are for the flag alone; the target can raise them (1.1). Full manual: https://nmap.org/book/man.html

`sudo` runs a command as root. Raw-packet scans (`-sS`, `-sU`, `-PR`, and the ping probes in `-sn`) need it; `-sT` does not.

**Targets**

| Flag | Meaning | Rating |
|---|---|---|
| `-iL $FILE` | "Read targets from a file, one per line." <br> Always use this with `scope.txt` or `live.txt`. | 🟢 |
| `--excludefile $FILE` | "Skip every host listed in the file." <br> Always use this with `exclude.txt`. | 🟢 |
| `--exclude-ports $LIST` | "Never scan these ports, even inside a range." <br> Used to protect OT ports. | 🟢 |
| `-sL` | List scan: lists targets, sends no probes. <br> Without `-n` it asks the DNS server for each name, so add `-n` unless you want the lookup (ladder step 4b). | 🟢 |

**Host discovery (is it up?)**

| Flag | Meaning | Rating |
|---|---|---|
| `-sn` | Ping sweep only: find live hosts, then stop. No port scan. | 🟢 |
| `-PE` | Send an ICMP echo request (an ordinary ping) | 🟢 |
| `-PS22,80` | Send a TCP SYN to the listed ports. A SYN/ACK or RST response indicates the host is up. | 🟢 |
| `-PA22,80` | Send a TCP ACK to the listed ports. A RST response indicates the host is up. Can help with some firewalls that block SYN probes, but stateful firewalls often block unsolicited ACKs too. | 🟢 |
| `-PR` | ARP request. Works only on a subnet we are directly connected to; very reliable there. | 🟢 |
| `-Pn` | Skip discovery and treat every address as up. Scans dead addresses too: slow and noisy. Use on one known host only. | 🟡 |

**Scan type (how ports are probed)**

| Flag | Meaning | Rating |
|---|---|---|
| `-sT` | TCP connect scan:<br>Completes the full handshake like a normal client. Needs no root. The gentle choice. | 🟢 |
| `-sS` | TCP SYN scan ("half-open"):<br> Sends a SYN and never completes the connection. Fast. Needs root (`sudo`). May trip IDS counters. | 🟢 |
| `-sU` | UDP scan, Slow: <br>Open ports usually stay silent and hosts rate-limit "port unreachable" replies, so nmap waits and retries. Needs root. | 🟡 |
| `-sA`, `-sF`, `-sX`, `-sN` | ACK, FIN, Xmas and Null scans:<br>Odd packets used to map firewalls.| 🟡 |

**Ports**

| Flag | Meaning | Rating |
|---|---|---|
| `-p $LIST` | Ports to scan (syntax in 1.5) | 🟢 for short lists |
| `-p-` | All 65,535 TCP ports | 🟡 |
| `--top-ports N` | The N most commonly open ports | 🟢 at 100, 🟡 at 1000 |
| `-F` | Fast: the top 100 ports. Same as `--top-ports 100`. | 🟢 |

**Detection (what is it?)**

| Flag | Meaning | Rating |
|---|---|---|
| `-sV` | Version detection:<br>Sends extra probes to get service names and versions | 🟡, 🔴 on OT |
| `-sC` | Run the default NSE scripts (same as `--script=default`) | 🟡, 🔴 on OT |
| `--script $NAME` | Run the named script, script list, or category (see the script tables below) | by script |
| `-O` | OS detection from how the host answers odd probes. Needs root. | 🟡 |
| `-A` | Aggressive: `-sV -sC -O` plus traceroute, all at once. Spell out what you want instead. | 🟡, 🔴 on OT |

**Speed**

| Flag | Meaning | Rating |
|---|---|---|
| `-T0` to `-T5` | Timing template, slowest to fastest. `-T3` is the default. | `-T2`/`-T3` 🟢, `-T4` 🟡, `-T5` 🔴 |
| `--max-rate N` | Never send more than N packets per second. Prefer this to `-T`. | 🟢 |
| `--max-retries N` | Give up on a port after N retransmissions | 🟢 |
| `--host-timeout T` | Give up on a host after time T (for example `5m`) | 🟢 |

**Watching a scan**

| Flag | Meaning | Rating |
|---|---|---|
| `-n` | No reverse DNS lookups. Faster. Hostnames given as targets are still resolved (`-R` forces reverse lookups). Used on every scan in this guide except the lookup step (4b). | 🟢 |
| `-v` | Verbose: print more as the scan runs (open ports as found). Use `-vv` for more. | 🟢 |
| `--stats-every T` | Print progress and an estimated finish time every T (for example `30s`) | 🟢 |
| `--open` | Show only hosts and ports that are open | 🟢 |
| `--reason` | Show why nmap chose each state (for example `syn-ack`, `conn-refused`, `no-response`) | 🟢 |
| `--resume $FILE` | Continue an interrupted scan from its saved output file | 🟢 |
| `--packet-trace` | Print every packet sent and received. Very long output; for learning on one host. | 🟢 |

**Output**

| Flag | Meaning | Rating |
|---|---|---|
| `-oA NAME` | Save all three formats: `NAME.nmap`, `NAME.gnmap`, `NAME.xml` | 🟢 |
| `-oN`, `-oG`, `-oX` | Save one format: normal, grepable, XML | 🟢 |

**Scripts named in this guide** (docs and full list: https://nmap.org/nsedoc/)

| Script | What it does | Categories | Rating |
|---|---|---|---|
| `smb-os-discovery` | Reads OS, computer name and domain from SMB | default, discovery, safe | 🟡 |
| `smb-protocols` | Lists which SMB versions the host accepts | safe, discovery | 🟡 |
| `smb2-security-mode` | Reports whether SMB signing is required | safe, discovery, default | 🟡 |
| `ms-sql-info` | Reads SQL Server version and instance names | default, discovery, safe | 🟡 |
| `ftp-anon` | Tries an anonymous FTP login (the one `auth` script we allow) | default, auth, safe | 🟡 |
| `smtp-commands` | Asks the mail server which commands it supports | default, discovery, safe | 🟡 |
| `smtp-enum-users` | Guesses mailbox names with `RCPT TO`, `VRFY` and `EXPN`. Only if the ROE allows. | auth, external, intrusive | 🔴 |
| `http-title` | Reads the page title | default, discovery, safe | 🟢 |
| `http-headers` | Reads the HTTP response headers | discovery, safe | 🟢 |
| `http-methods` | Lists which HTTP methods the server allows | default, safe | 🟡 |
| `rdp-enum-encryption` | Reads which RDP security settings and encryption levels the host offers | safe, discovery | 🟡 |

Categories were checked on each script's nmap.org/nsedoc page.

**Script categories**

| Category | What it means | Rating |
|---|---|---|
| `safe`, `discovery`, `default` | Mostly read-only information gathering | 🟡 |
| `version` | Supports `-sV` | 🟡 |
| `intrusive` | Can crash services or use lots of resources | 🔴 |
| `brute` | Guess credentials: can lock accounts. Not recon. | 🔴 |
| `auth` | Check or bypass authentication. `ftp-anon` is the one we allow (🟡); any other `auth` script is 🔴. | 🔴 |
| `external` | Contacts third-party servers, so it can leave scope (1.2) | 🔴 |
| `fuzzer` | Sends unexpected or malformed input | 🔴 |
| `malware` | Looks for malware on the target; not recon | 🔴 |
| `vuln` | Vulnerability checks; some trigger the bug. Past incident: 1.4. | 🔴 |
| `dos`, `exploit` | Never run in recon | Prohibited |

Read a script's page on https://nmap.org/nsedoc/ (one per script, with categories) before running it. Usage: https://nmap.org/book/nse-usage.html

## 1.7 The nmap ladder, simple to complex

Climb one rung at a time.

| # | Goal | Command | Rating | Why, and what raises it |
|---|---|---|---|---|
| 0 | List targets, send nothing | `nmap -sL -n -iL scope.txt --excludefile exclude.txt` | 🟢 | Nothing. `-n` means no name lookups for addresses. |
| 1 | Which hosts are up (ping only) | `sudo nmap -sn -n -PE -iL scope.txt --excludefile exclude.txt -oA disc-icmp` | 🟢 | `-sn` means no port scan; few packets per host. |
| 2 | Same, with TCP probes (hosts that ignore ping) | `sudo nmap -sn -n -PS22,80,135,443,445,3389 -iL scope.txt --excludefile exclude.txt -oA disc-syn` | 🟢 | `-PS` sends SYNs to a handful of ports only |
| 3 | Other probe types | `-PA22,80,443,3389` (ACK) → `disc-ack`; `-PR` (ARP, only on a subnet we sit on directly) → `disc-arp`. Add `-n` and `sudo` as in step 1. | 🟢 | Same as steps 1 and 2: few packets per host. |
| 4 | Merge live hosts | `cat disc-*.gnmap \| awk '/Up$/{print $2}' \| sort -uV > live.txt` | 🟢 | Local file work |
| 4b | Names, once | `nmap -sL -iL live.txt --excludefile exclude.txt -oN names.txt` | 🟢 | The only scan without `-n`: asks our DNS server for each live host's name. Run once; copy the names into `hosts.csv`. First check the DNS server (1.9) is in `scope.txt`; if not, skip this step and ask Operations (R12). If it is a client domain controller, this is traffic to an in-scope host: say it aloud first. |
| 5 | First look at ports | `nmap -n --top-ports 100 --max-rate 100 --exclude-ports <OT-string> -iL live.txt --excludefile exclude.txt -oA top100` | 🟢 | `--top-ports 100` limits probes; `--max-rate 100` caps packets per second |
| 6 | Wider | `nmap -n --top-ports 1000 --exclude-ports <OT-string> -iL <claimed-hosts> --excludefile exclude.txt -oA top1000` | 🟡 | 10× more probes than step 5. Claimed hosts only (Part 7). |
| 7 | All TCP ports, one host | `nmap -n -p- --max-rate 300 --exclude-ports <OT-string> <host> -oA full-<host>` | 🟡 | `-p-` is 65,535 probes per host. Never on a whole range in one go. |
| 8 | What is on an open port | `nmap -n -sV -p <open-ports> <host> -oA ver-<host>` | 🟡, 🔴 on OT | `-sV` sends extra probes to elicit banners; some fragile services react badly |
| 9 | Default scripts | `nmap -n -sC -p <open-ports> <host>` | 🟡, 🔴 on OT | `-sC` runs scripts in the `default` category; some touch services in ways simple scans do not |
| 10 | UDP, the useful ones | `sudo nmap -n -sU --top-ports 20 --max-rate 50 <host>` | 🟡 | `-sU` is slow and retries; keep ports few and the rate low |
| 11 | Chosen scripts | `nmap -n --script <name> -p <port> <host>` | by script | See "Script categories" in 1.6 |

**Why `-n` on every scan, and one lookup.** Hostnames hint at what a host does (`dc01`, `web-app`, a name that sounds like a controller), so we look them up once, in step 4b, against `live.txt` only. Every other scan uses `-n`: less traffic, faster, no reverse lookups leaving scope (the DNS server in `/etc/resolv.conf` may be outside the SOW, see 1.2), and the names are already known.

On a subnet we sit on directly, nmap uses ARP instead of ping (steps 1 to 3 then give the same result); the ping and TCP probes matter for hosts behind a router.

`<claimed-hosts>`: a plain text file of your claimed hosts (Part 7; see the box "Where target addresses come from" in 1.2), one IP per line, in `~/cptc-work/field-notes/<yourname>/recon/`. Every address must also be in `scope.txt` (1.2). Each lane keeps its own copy, for example `win-hosts.txt`.

Flags in the ladder are explained in 1.6. After any scan from step 5 on, run the health check in 1.10. Scan types: https://nmap.org/book/man-port-scanning-techniques.html. Timing templates: https://nmap.org/book/performance-timing-templates.html

## 1.8 Output and naming

Always save output with `-oA <name>` (writes `.nmap`, `.gnmap` and `.xml` at once). Docs: https://nmap.org/book/man-output.html

| Thing | Convention |
|---|---|
| Working folder | `~/cptc-work/field-notes/<yourname>/recon/` (the team README's pull list already includes `field-notes/`) |
| Scan file names | `<scan>-<target>-<HHMM>` for example `top100-10.0.5.0_24-1032`. Add the time when you run the same scan twice; short names like `top100` are fine otherwise. |
| Scope files | `scope.txt`, `exclude.txt`, `live.txt` in `~/cptc-work/` (the `.gitignore` already lists `scope.txt` and `live.txt`) |
| Terminal log | Every terminal runs in the logged shell (`scripts/logged-shell.md`, R5). Logs are the evidence for incident reports. |
| Dates and times | `HH:MM` 24-hour local, `YYYY-MM-DD` |
| Nothing in the git clone | Scan output stays in `~/cptc-work`, never in the repo (R2, R3) |

## 1.9 Zero-packet first steps

Learn the network before sending anything to a target. These commands only read our own machine's settings or listen. Apart from traceroute at the end, nothing here probes a target: all 🟢.

**Where are we?**

| Question | Linux (Kali) | Windows | Tells you |
|---|---|---|---|
| Our address and subnet | `ip a` | `ipconfig /all` | The subnet we sit on directly. ARP discovery (`-PR`) works there. |
| Our routes | `ip r` | `route print` | The default gateway, and any other subnets we were given a route to |
| Our DNS server | `cat /etc/resolv.conf` | `ipconfig /all` (look for "DNS Servers") | Often a domain controller. Write it on the whiteboard. |
| Hosts we already know | `ip neigh` | `arp -a` | Neighbors our machine has talked to: a free list of live hosts |

Compare what you find with `scope.txt`. A subnet we sit on that is **not** in the SOW is a question for Operations (R12), not a scan target.

**Listen, don't send**

Hosts announce themselves with broadcast and multicast packets that every machine on the segment receives. Listening costs the target nothing.

```
sudo tcpdump -i <interface> -n -w listen-<HHMM>.pcap arp or udp port 137 or udp port 5353 or udp port 5355 or udp port 67
```

| Part | Meaning |
|---|---|
| `sudo` | Capturing packets needs root |
| `-i <interface>` | Which network interface to listen on (`ip a` shows the names, for example `eth0`) |
| `-n` | Do not look up names (faster, and sends no DNS queries) |
| `-w FILE` | Save the packets to a file you can open in Wireshark. This is evidence. |
| `arp` | Who-has requests: hosts looking for each other |
| `udp port 137` | NetBIOS name service: Windows hosts announcing their names |
| `udp port 5353` | mDNS: devices announcing services on the local network |
| `udp port 5355` | LLMNR: Windows hosts asking for names |
| `udp port 67` | DHCP: hosts joining the network, and the DHCP server's address |

Ask Operations at kickoff whether listening is allowed (R12): it sends nothing, but network activity may be logged (rulebook p7) and monitoring systems are off limits (p4). If allowed, run it for a few minutes while the SOW is read, then read it back with `tcpdump -nr listen-<HHMM>.pcap | head -50` (`-r` reads a saved file) or in Wireshark (https://www.wireshark.org/docs/). Docs: https://www.tcpdump.org/manpages/tcpdump.1.html

**Limits.** On a switched network you only see broadcast, multicast, and traffic to or from your own machine, not other hosts' private conversations. **Listening is not poisoning.** Tools that answer name requests (Responder and similar) are a different action, covered by `checklists/10-ad-internal.md` and the ROE.

**Gateways between subnets**

| Linux | Windows | Meaning |
|---|---|---|
| `traceroute -n <host>` | `tracert -d <host>` | Lists each router on the way to a host. `-n` / `-d`: do not look up names. Each hop is a gateway between subnets. |

Sends a few packets toward one host: 🟢 for one in-scope host. Do not trace to hosts outside scope.

**What to write down:** our address and subnet, the gateway, the DNS server, hosts seen on the wire, and any subnet we sit on. Put new hosts in `hosts.csv` with the stage set to "seen, not scanned".

## 1.10 Watching a scan and checking afterward

A scan isn't finished when the prompt returns. Watch it, then check the targets.

**While it runs.** For scans over a minute:

| Flag or key | Meaning |
|---|---|
| `--stats-every 30s` | Progress and estimated finish every 30 seconds. If the estimate is hours, stop and reduce the scan. |
| Press `Enter` during a scan | Status line, no flag needed |
| `Ctrl-C` | Stops the scan. `-oA` output is partial but usable. |

**How long should it take?** At least probes ÷ rate. Use it to tell slow from stuck:

| Scan | Probes | Rate | At least |
|---|---|---|---|
| Top 100 ports, one host (step 5) | 100 | 100 per second | about 1 second |
| Top 100 ports, a /24 of 254 live hosts (step 5) | 25,400 | 100 per second | about 4 minutes |
| All TCP ports, one host (step 7) | 65,535 | 300 per second | about 3.5 minutes |
| Top 20 UDP ports, one host (step 10) | 20, plus retries | 50 per second | under a second; often minutes, because UDP retries |

Retries and slow hosts add time. **If `--stats-every` shows more than ten times these numbers, stop and ask why.**

**If a scan stops or you stop it,** resume instead of starting over: `nmap --resume <name>.nmap`.
- Needs `-oN` or `-oA` output. Resume from the normal or grepable file.
- Same targets and options.

**After every scan,** run the health check. Compare only scans of the same kind:

1. **Are the hosts still up?** Re-run the ping sweep on the same target file: `sudo nmap -sn -n -PE -iL <targets> -oA after-<HHMM>`. 🟢
   - The "before" is ladder step 1's `disc-icmp.xml`.
2. **Compare ping sweep to ping sweep** with `ndiff`, which ships with nmap (https://nmap.org/ndiff/): `ndiff disc-icmp.xml after-<HHMM>.xml`.
   - Hosts that disappeared or appeared print as `-` and `+` lines.
   - **Never compare a port scan against a ping sweep.** Every port looks removed and falsely triggers the stop rule.
3. **Fragile hosts: re-check the open ports too.** A ping shows a host went down, not a crashed service. `nmap -sT -n -p <the ports open before> <host> -oA recheck-<host>-<HHMM>`, then `ndiff` it against that host's earlier port scan XML. 🟢
4. **Something disappeared:** R10 applies. Stop, say it aloud, note the time and the command, and follow 1.3. Don't rerun the scan just to check.
5. **Nothing changed:** note "no change" next to the scan. It's evidence for an incident report if something breaks later.

`ndiff` needs XML, so always scan with `-oA` (1.8).

## 1.11 Reading nmap output, and when nothing shows up

**Example of normal nmap output** (made-up host; the line numbers on the left are not part of the output):

```
1  # Nmap 7.95 scan initiated Fri Oct 30 10:32:11 2026 as: nmap -n --top-ports 100 --max-rate 100 -oA top100 10.0.5.20
2  Nmap scan report for 10.0.5.20
3  Host is up (0.0021s latency).
4  Not shown: 96 closed tcp ports (conn-refused)
5  PORT     STATE    SERVICE
6  22/tcp   open     ssh
7  80/tcp   open     http
8  443/tcp  open     https
9  3306/tcp filtered mysql
10 # Nmap done at Fri Oct 30 10:32:14 2026 -- 1 IP address (1 host up) scanned in 2.91 seconds
```

| Line | What it tells you |
|---|---|
| 1 | The exact command and the start time. Keep this with the output: it is the reproduction step. |
| 2 | The host. With `-n` there is no name in front; names come from the one lookup in ladder step 4b (`names.txt`). |
| 3 | The host answered. "Latency" is the round trip; a very high number means a slow link or a busy host. |
| 4 | Ports in the scan that were closed, summarized. `conn-refused` means the host actively said no, so it is reachable. |
| 5-9 | Ports that are not closed. Service names are guessed from the port number until you run `-sV`. |
| 9 | `filtered`: no answer, usually a firewall. The port might be open behind it; it is not "closed". |
| 10 | The end time, how many hosts answered, and how long it took. |

**Nothing shows up: first checks**

| Symptom | Likely cause | What to do |
|---|---|---|
| "0 hosts up" on a range that must have hosts | Ping is blocked | Try the TCP probes (ladder steps 2 and 3). On one known host, `-Pn` to skip discovery. |
| Many hosts show every port filtered | A firewall drops our probes | Do not raise the rate. Try `-sT` against a known port, and note the firewall as a finding. |
| Scan is very slow | DNS lookups, high retries, or a rate cap | Add `-n` (no DNS). Check `--stats-every`. Do not remove `--max-rate` to speed it up. |
| Results differ between runs | Hosts moved, firewall rules, or the host is struggling | Run `ndiff` (1.10). If a host got worse, stop (1.3). |
| `-sS`, `-sU`, `-O` or `-PR` stops with "requires root privileges" | Missing `sudo` | Put `sudo` in front. (A scan with no scan type given quietly runs as `-sT` instead.) |
| "No route to host" or "Network unreachable" | We have no route to that subnet | Check `ip r` (1.9). Ask Operations if a route was expected. |
| Host is up but only odd ports are open | Non-standard setup, or an OT/embedded device | Identify one port at a time (`-sV -p <port>`) and treat a device as OT-adjacent until shown otherwise |
| Output file missing | Forgot `-oA` | Rerun the same scan on the same hosts only if it was 🟢; for 🟡, say it aloud first (1.1) |
| Windows: no results at all | Npcap not installed, or PowerShell not run as Administrator | Install Npcap; reopen PowerShell as Administrator |

## 1.12 First-hour sequence for the whole team

Run in order; each step finishes before the next starts.

1. Read the SOW and ROE aloud. Write ranges and exclusions on the whiteboard (`checklists/00-kickoff.md`).
2. Build `scope.txt` and `exclude.txt`. Run the step 0 preview and compare the count to the SOW.
3. **Zero-packet steps** (1.9): our address, gateway and DNS server, and a few minutes of listening. Write down what you find. 🟢
4. **Discovery sweeps** (ladder steps 1 to 4) on `scope.txt` with `--excludefile exclude.txt` (the SOW exclusions and known OT hosts). 🟢 If the SOW names a range as OT or ride control, say so aloud and confirm with Operations before sweeping it: some devices fall over from plain host discovery (`checklists/30-ot-ics-safe.md`).
5. **OT-finding pass**, only if the SOW or hostnames suggest OT. 🟡 First say it aloud to the team and confirm the ROE allows scanning OT (`checklists/30-ot-ics-safe.md`). Put the suspected OT ranges (a subset of `scope.txt`) in `ot-ranges.txt`, then:

   ```
   nmap -sT -n -p 102,502,2404,4840,20000,44818 --max-rate 10 --max-retries 1 -iL ot-ranges.txt --excludefile exclude.txt -oA ot-find
   ```

   TCP connect, specific ports, ten packets per second, no version probes, no scripts, targets from a file. TCP only: BACnet (47808/UDP) is not checked; ask before adding a UDP check. Hits go on the whiteboard and into `exclude.txt` tagged `# OT`.
6. **Names, once** (ladder step 4b) on `live.txt`. 🟢 Copy the names into `hosts.csv`.
7. **IT port pass** (ladder step 5) on `live.txt` minus OT. 🟢
8. **Health check** (1.10): re-ping, compare with `ndiff`.
9. Route hosts to lanes and claim them (Part 7).

---

# Part 2: Windows / Active Directory

Goal: find the domain controllers, learn the domain name, see what each Windows host offers without a password, and note what is misconfigured. Stop at enumeration. Every target is a claimed host (Part 7) that is in `scope.txt` (1.2). Never type a range.

Tools: nmap, NetExec (`nxc`, docs https://www.netexec.wiki/), smbclient (https://www.samba.org/samba/docs/current/man-html/smbclient.1.html), rpcclient, ldapsearch (https://www.openldap.org/software/man.cgi?query=ldapsearch), enum4linux-ng (https://github.com/cddmp/enum4linux-ng), dig.

## 2.1 Ports that point to Windows

| Port | Service | Says |
|---|---|---|
| 53 | DNS | Often a domain controller |
| 88 | Kerberos | **Domain controller** |
| 135, 139, 445 | RPC, NetBIOS, SMB | Windows file and print services |
| 389, 636, 3268, 3269 | LDAP, LDAPS, Global Catalog | **Domain controller** |
| 1433 | MSSQL | SQL Server |
| 3389 | RDP | Remote Desktop |
| 5985, 5986 | WinRM | Remote management |
| 9389 | AD Web Services | Domain controller |

A host with 88 and 389 open is a DC. Write it on the whiteboard as soon as you see it; DCs are shared infrastructure and get extra care (see 2.6).

## 2.2 Flags used in this part

nmap flags are in 1.6. The other tools:

**NetExec (`nxc`)**: `nxc <protocol> <target> [options]`. Protocol is `smb`, `ldap` or `winrm` in this guide; target is an IP, a range, or a file of hosts.

| Flag | Meaning | Rating |
|---|---|---|
| (no options) | Connect, read the host name, domain and SMB signing setting, log nothing in | 🟢 |
| `-u USER` | Username to log in as. `''` (empty) means a null session; `guest` is the built-in guest account. | 🟡 Noisy: one login attempt, logged |
| `-p PASS` | Password. `''` means empty. | 🟡 Noisy: one login attempt, logged |
| `--shares` | List shares and what access the account has | 🟢 |
| `--users` | List domain users (works with `ldap`, and with `smb`) | 🟡 |
| `--pass-pol` | Show the domain password policy: minimum length and **lockout threshold** | 🟢 |
| `--gen-relay-list FILE` | Write the hosts that do not require SMB signing to FILE | 🟢 |

These NetExec flags are not yet checked against its documentation: confirm them with `nxc smb -h` and `nxc ldap -h` on our Kali image before relying on them.

**smbclient** (`smbclient //HOST/SHARE -N`)

| Part | Meaning |
|---|---|
| `//HOST/SHARE` | The share to open |
| `-N` | No password: connect anonymously, do not prompt |
| `ls` (typed at the prompt) | List files. Read-only; do not use `put` or `del`. |

**rpcclient** (`rpcclient -U "" -N HOST -c enumdomusers`)

| Flag | Meaning |
|---|---|
| `-U ""` | Log in with an empty username |
| `-N` | No password |
| `-c "COMMAND"` | Run one command, then exit. `enumdomusers` lists domain users. |

**ldapsearch** (`ldapsearch -x -H ldap://DC -b "" -s base namingContexts`)

| Flag | Meaning |
|---|---|
| `-x` | Simple authentication; with no `-D` (the account to log in as) and `-w` (its password) it is anonymous |
| `-H URI` | The server: `ldap://host` for port 389, `ldaps://host` for port 636 |
| `-b ""` | Where to start searching. The empty base is the server's root entry. Without `-b`, the base may come from a config file. |
| `-s base` | Search scope: only the root entry, nothing below it |
| `namingContexts` | The attribute to return: which directory trees the server holds, including the domain name |

**dig** (`dig @SERVER NAME TYPE`)

| Part | Meaning |
|---|---|
| `@SERVER` | Ask this DNS server instead of the default |
| `ANY` | Ask for all record types (some servers refuse) |
| `SRV` | Service records; `_ldap._tcp.dc._msdcs.DOMAIN` finds domain controllers |
| `AXFR` | Zone transfer: ask for the whole zone. 🟡; a finding if it works. |

**enum4linux-ng** `-A`: all the simple checks (users, groups, shares, policies, OS information). It does not do RID cycling (`-R`); do not add it. 🟡: many connections to one host.

**PowerShell**: `Test-NetConnection HOST -Port N` checks one port; `Start-Transcript` logs the session to a file.

## 2.3 Step by step

| # | Goal | Command | Rating | Why, and what raises it |
|---|---|---|---|---|
| 1 | Windows ports on a claimed host | `nmap -sT -n -p 53,88,135,139,389,445,636,1433,3389,5985 <host> -oA win-<host>` | 🟢 | Specific ports only |
| 2 | Name, domain, SMB signing for a list | `nxc smb <claimed-hosts>` | 🟢 | One SMB connection per host; no login attempt |
| 3 | Which hosts do not require signing | `nxc smb <claimed-hosts> --gen-relay-list relay.txt` | 🟢 | Writes a list. This is a **finding**. Do not relay anything. |
| 4 | DNS records for the domain | `dig @<dc> <domain> ANY` and `dig @<dc> _ldap._tcp.dc._msdcs.<domain> SRV` | 🟢 | Normal DNS lookups |
| 5 | Zone transfer allowed? | `dig @<dc> <domain> AXFR` | 🟡 | One request, but it pulls the whole zone; tell the team first |
| 6 | Anonymous LDAP (naming contexts) | `ldapsearch -x -H ldap://<dc> -b "" -s base namingContexts` | 🟢 | Reads the root entry only |
| 7 | Anonymous LDAP users | `nxc ldap <dc> -u '' -p '' --users` | 🟡 | Larger read. Usually fails on current domain controllers; a finding if it works. |
| 8 | SMB null session shares | `nxc smb <dc> -u '' -p '' --shares` | 🟡 | One login attempt as an empty user. Logged as a failed or anonymous login. |
| 9 | Guest session shares | `nxc smb <dc> -u 'guest' -p '' --shares` | 🟡 | One attempt as `guest`. Logged. |
| 10 | Browse an open share | `smbclient //<host>/<share> -N` then `ls` | 🟢 | Read-only listing. Do not `put` or `del`. |
| 11 | Password policy (null session) | `nxc smb <dc> -u '' -p '' --pass-pol` | 🟡 | A null-session login that reads the policy. **Read the result before any guessing against named accounts (2.4)**: it tells you the lockout threshold. |
| 12 | RPC enumeration of users | `rpcclient -U "" -N <dc> -c enumdomusers` | 🟡 | A finding if it works |
| 13 | All of the above in one go | `enum4linux-ng -A <host>` | 🟡 | `-A` runs all the simple checks; many connections. One host at a time. |
| 14 | Nmap SMB scripts, informational | `nmap -n -p 445 --script smb-os-discovery,smb-protocols,smb2-security-mode <host>` | 🟡 | Named scripts only; read what each does first. `smb-os-discovery` returns little on hosts that speak only SMB2 or newer; `nxc smb` (step 2) already shows the OS and domain. |
| 15 | MSSQL discovery (info only) | `nmap -n -p 1433 --script ms-sql-info <host>` | 🟡 | Reads version and instance info |

Steps 8, 9 and 11 are logins: 🟡, said aloud. Null and guest attempts do not risk locking real accounts. Read the lockout threshold (step 11) before any guessing against named accounts (2.4); a threshold of 1 to 3 means ask Operations first.

`<claimed-hosts>` is defined in 1.7; for this lane keep a copy such as `win-hosts.txt`.

**Checklist 10 agrees.** Step 1 of `checklists/10-ad-internal.md` runs `nmap -sC -sV` with the same 🟡 label and the same condition (claimed, non-OT hosts only, one host at a time). If they ever differ, the stricter condition applies (1.5).

## 2.4 Not recon: stop and ask (🔴)

| Action | Why risky |
|---|---|
| Guessing passwords, even "just a few" (spraying) | Can lock users out of the client's systems; needs the lockout policy from step 11 and an approval first |
| `kerbrute`/user guessing at scale | Floods the DC's logs; noisy |
| nmap `brute`, `vuln`, `intrusive` script categories (`smb-vuln-*`, `ms-sql-brute`) | Can crash services or lock accounts |
| Poisoning tools (Responder, mitm6) | Intercepts other users' traffic; many ROEs bar it |
| Running anything with a credential against many hosts | Counts as authenticated testing; follows `checklists/10-ad-internal.md` and the ROE |

Authenticated enumeration (BloodHound, shares with credentials, Kerberos checks) is covered in `checklists/10-ad-internal.md`.

## 2.5 What to write down

**Per Windows host:** one row in `hosts.csv`: IP, hostname, OS, role (DC, file server, workstation), open ports, owner, notes.
- **Per DC, also:** domain name, NetBIOS name, functional level if shown.
- **Findings** (SMB signing off, null session, anonymous LDAP): get a finding ID the moment you see them (R6). Save the exact command and output.

## 2.6 Care on domain controllers

A DC serves logins for the whole client. Treat it as 🟡 by default for everything: one host at a time, `--max-rate` set, no `-T4`, no script categories beyond `default`. If a DC stops answering, stop and follow 1.3.

## 2.7 Windows laptop notes

Quick checks from your Windows box, nothing to install:

| Task | Command | Rating |
|---|---|---|
| Is a port open | `Test-NetConnection <host> -Port 445` (PowerShell) | 🟢 |
| DNS | `nslookup <name> <dc>` | 🟢 |
| Windows view of SMB | `net view \\<host>` | 🟢 from a local test account; 🟡 if signed in with a domain account (it sends those credentials) |
| Nmap on Windows | Same syntax; needs Npcap installed; run PowerShell as Administrator for ARP/SYN | same as Linux |

PowerShell transcript: `Start-Transcript` at the start of every session (R5).

---

# Part 3: Linux

Goal: for each Linux or Unix-like host, learn what it runs, which versions, and which services are exposed without a login. Stop at enumeration. Every target is a claimed host (Part 7) that is in `scope.txt` (1.2). Never type a range.

Tools: nmap, ssh-audit (https://github.com/jtesta/ssh-audit), showmount and rpcinfo (https://linux.die.net/man/8/showmount), snmpwalk (http://www.net-snmp.org/docs/man/snmpwalk.html), onesixtyone (https://github.com/trailofbits/onesixtyone), curl, nc.

## 3.1 Ports that point to Linux services

| Port | Service | Says |
|---|---|---|
| 22 | SSH | Remote shell |
| 21 | FTP | File transfer, sometimes anonymous |
| 25, 465, 587 | SMTP | Mail |
| 111 | rpcbind | NFS and other RPC |
| 2049 | NFS | File shares |
| 161/UDP | SNMP | Device info, often network gear too |
| 3306, 5432, 6379, 27017 | MySQL, PostgreSQL, Redis, MongoDB | Databases |
| 873 | rsync | File sync |
| 8080, 8443, 9000 | Alt web | Hand to the Web lane |

## 3.2 Flags used in this part

nmap flags are in 1.6. The other tools:

| Tool and flag | Meaning | Rating |
|---|---|---|
| `nc -nv HOST PORT` | netcat. `-n`: no DNS lookups. `-v`: verbose, prints that it connected. Shows the banner a service sends on connect. | 🟢 |
| `ssh-audit HOST` | Connects once and lists the key exchange, cipher and MAC algorithms the SSH server offers, flagging weak ones. No flags needed. | 🟢 |
| `rpcinfo -p HOST` | `-p`: probe the portmapper (port 111) and list the RPC programs registered | 🟢 |
| `showmount -e HOST` | `-e`: show the NFS export list (which folders are shared and to whom) | 🟢 |
| `onesixtyone -c FILE HOST` | `-c FILE`: file of SNMP community strings (like passwords) to try. Keep it to `public`, `private`, `community`. | 🟡 |
| `snmpwalk -v2c -c COMMUNITY HOST [OID]` | `-v2c`: SNMP version 2c. `-c`: the community string. The optional last word (for example `system`) limits the walk to that subtree; without it, the whole `mib-2` tree is read (not the vendor-specific parts). | 🟢 with `system`, 🟡 without |

## 3.3 Step by step

| # | Goal | Command | Rating | Why, and what raises it |
|---|---|---|---|---|
| 1 | Linux ports on a claimed host | `nmap -sT -n -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host> -oA lin-<host>` | 🟢 | Specific ports only |
| 2 | SSH banner | `nc -nv <host> 22` (Ctrl-C after the banner) | 🟢 | One connection |
| 3 | SSH algorithms and version issues | `ssh-audit <host>` | 🟢 | One connection; reads what the server offers; findings for old algorithms |
| 4 | Version of one open port | `nmap -n -sV -p <port> <host>` | 🟡 | `-sV` sends extra probes; one port, one host |
| 5 | FTP anonymous login allowed? | `nmap -n -p 21 --script ftp-anon <host>` | 🟡 | One login attempt as `anonymous`. A finding if it works. The one `auth` script we allow (1.6). |
| 6 | RPC services | `rpcinfo -p <host>` | 🟢 | Lists registered RPC programs |
| 7 | NFS exports | `showmount -e <host>` | 🟢 | Lists exported shares. A world-readable export is a finding. |
| 8 | SNMP community check | `onesixtyone -c community.txt <host>` | 🟡 | Guesses community strings; keep the list to `public`, `private`, `community`; one host at a time |
| 9 | SNMP read (if `public` works) | `snmpwalk -v2c -c public <host> 1.3.6.1.2.1.1` | 🟢 | `1.3.6.1.2.1.1` is `system` (name, location, uptime) in numeric form, which works without the MIB name files installed; if `system` works on our Kali image, either is fine. A finding if it answers. |
| 10 | Wider SNMP read | `snmpwalk -v2c -c public <host>` | 🟡 | Walks the whole `mib-2` tree; large output; slow on small devices |
| 11 | SMTP banner and commands offered | `nmap -n -p 25 --script smtp-commands <host>` | 🟡 | Asks the server what it supports |
| 12 | SMTP user check | `nmap -n -p 25 --script smtp-enum-users <host>` | 🔴 | Guesses names with `RCPT TO`, `VRFY` and `EXPN`. Categories `auth`, `external`, `intrusive`. Only if the ROE allows, with an approval line. |
| 13 | Database banners | `nmap -n -sV -p 3306,5432,6379,27017 <host>` | 🟡 | Version probes against databases |
| 14 | Redis open without password? | `nc -nv <host> 6379` then type `PING` | 🟢 | `+PONG` with no auth is a finding. Do not run other commands. |
| 15 | Web ports found | Hand to Part 4 | n/a | |

Input files, built by hand: `printf 'public\nprivate\ncommunity\n' > community.txt` (three guesses, one per line); `<claimed-hosts>` is defined in 1.7, and for this lane keep a copy such as `lin-hosts.txt`.

## 3.4 Not recon: stop and ask (🔴)

| Action | Why risky |
|---|---|
| SSH or FTP login guessing (`hydra`, nmap `*-brute` scripts) | Locks accounts; floods logs; can ban our own address |
| Mounting an NFS share to read or write | Reading files may be fine and writing is not; ask first, and mount read-only (`-o ro`) |
| Redis/database commands past `PING` or a version | Reads data or changes it |
| `snmpset` | Writes to the device |
| nmap `intrusive`, `vuln`, `brute` script categories | See 1.6 |

## 3.5 What to write down

**Per host:** one row in `hosts.csv`: IP, hostname, OS guess (from banners, not from `-O`), role, open ports, owner.
- **Per service:** the version string exactly as shown (needed for the report's reproduction steps).
- **Findings** (anonymous FTP, open NFS, default SNMP community, old SSH algorithms): get a finding ID right away (R6).

## 3.6 Linux-specific cautions

- Embedded Linux (cameras, kiosks, building controllers, routers) fails more easily than a server. When `ssh-audit` or a banner shows a device vendor name, treat the host as OT-adjacent and use the slow pass from 1.12.
- A service that stops answering after your probe: stop and follow 1.3.

---

# Part 4: Web applications

Goal: find every web service, map what each one is made of, and note the obvious exposures. Stop at mapping. Testing logic and inputs follows `checklists/20-web-app.md`.

Tools: nmap, httpx-toolkit (ProjectDiscovery httpx, https://github.com/projectdiscovery/httpx), whatweb (https://github.com/urbanadventurer/WhatWeb/wiki), gowitness (https://github.com/sensepost/gowitness), curl (https://curl.se/docs/manpage.html), ffuf (https://github.com/ffuf/ffuf), gobuster (https://github.com/OJ/gobuster), nikto (https://github.com/sullo/nikto/wiki), sslscan or testssl.sh (https://testssl.sh/), Burp Community (https://portswigger.net/burp/documentation). The team picks one proxy to practice; Burp is the default here.

## 4.1 Flags used in this part

nmap flags are in 1.6. The other tools:

**Input files.**
- `urls.txt`: one full URL per line, written by hand from the web ports found in 4.2 step 1 (for example `http://10.0.5.20:8080`), plus any URL in `scope-web.txt`. Every host in it must be in `scope.txt` or `scope-web.txt` (1.2).
- `<wordlist>`: one word per line. Start with `/usr/share/wordlists/dirb/common.txt` (check the path on our Kali image).

On Kali the ProjectDiscovery tool is installed as `httpx-toolkit`. A plain `httpx` there is a different program (a Python HTTP client), so every command here uses `httpx-toolkit`.

**httpx-toolkit** (`httpx-toolkit -l urls.txt -title -status-code -tech-detect -rate-limit 10 -duc`)

| Flag | Meaning |
|---|---|
| `-l FILE` | Read URLs or hosts from a file |
| `-title` | Print each page's title |
| `-status-code` | Print the HTTP status (200 ok, 301 redirect, 401 login needed, 403 forbidden, 404 missing) |
| `-tech-detect` | Guess the technology used from headers and page content |
| `-u URL` | One URL instead of a file |
| `-rate-limit N` | At most N requests per second |
| `-duc` | Do not check for updates on start (the check is a lookup to the Internet, see 1.2) |

On Kali the ProjectDiscovery tool may be installed as `httpx-toolkit`, and plain `httpx` may be the Python library's command. Run `httpx -version` and `httpx -h` on our Kali image first; if there is no `-title`, use `httpx-toolkit` in every command below.

**curl** (`curl -sI URL`)

| Flag | Meaning |
|---|---|
| `-s` | Silent: no progress meter |
| `-I` | Ask for the headers only (a HEAD request) |

**whatweb** `-a N`: aggression level 1 to 4.
- **1** (default): one request per target, but it follows redirects, so check the final address is in scope.
- **3:** extra requests for plugins that matched. **4:** many.
- Rating: 🟢 at 1, 🟡 at 3 and up.

**gowitness** (`gowitness scan file -f urls.txt`): `scan file` reads URLs from the file named by `-f` and screenshots each page.
- Version 3 syntax. Add `--write-db` to keep results in its database. Flags differ between versions: check `gowitness scan file -h` on our Kali image.
- Its browser follows redirects and loads images and scripts from other sites. Check the URLs in `urls.txt` are in scope first.

**sslscan / testssl.sh** `HOST:PORT`: connects several times with different TLS settings to see which protocols and ciphers the server accepts. With no options both also run test probes for known TLS bugs (Heartbleed and similar), which send crafted messages.

**ffuf** (`ffuf -u http://HOST/FUZZ -w LIST -rate 20 -t 5`)

| Flag | Meaning |
|---|---|
| `-u URL` | The URL. The word `FUZZ` is replaced by each word from the list. |
| `-w FILE` | The wordlist |
| `-rate N` | At most N requests per second |
| `-t N` | N threads (requests in flight at once). The default is 40. |

**gobuster** (`gobuster dir -u URL -w LIST -t 2 --delay 200ms`)

| Part | Meaning |
|---|---|
| `dir` | Directory and file mode |
| `-u`, `-w` | URL and wordlist, as in ffuf |
| `-t N` | N threads |
| `--delay T` | Each thread pauses T between its own requests (5 threads at 100ms is up to 50 requests per second) |

**nikto** (🔴): `-h HOST` sets the target; `-Tuning CODES` chooses which checks run.
- Use `-Tuning 1,2,3` (interesting files, misconfiguration, information disclosure).
- **Never** 5, 6, 9 or `a` (remote file retrieval, denial of service, SQL injection, authentication bypass).
- Check the code list with `nikto -H` on our Kali version.

**Burp Community**: no flags; a proxy you point the browser at.

## 4.2 Find every web service

HTTP hides on odd ports. Step 1 checks the common ones; also check 9090, 3000 and 5000 on hosts that look like web servers. After the service scan, anything nmap labels `http`, `https`, `http-proxy` or `ssl/http` belongs here.

| # | Goal | Command | Rating | Why, and what raises it |
|---|---|---|---|---|
| 1 | Web ports on a claimed host | `nmap -sT -n -p 80,443,8000,8008,8080,8081,8443,8888,9000 <host> -oA web-<host>` | 🟢 | Specific ports only |
| 2 | Which URLs respond, with title and status | `httpx-toolkit -l urls.txt -title -status-code -tech-detect -rate-limit 10 -duc` | 🟢 | `-rate-limit 10` caps requests per second |
| 3 | Look at one page | `curl -sI http://<host>:<port>/` | 🟢 | One request, headers only |
| 4 | Fingerprint technology | `whatweb http://<host>:<port>` | 🟢 | Default aggression (`-a 1`) is a single request. `-a 3` and `-a 4` send many requests: 🟡 |
| 5 | Screenshots of every site | `gowitness scan file -f urls.txt` | 🟢 | Redirects or links can load pages outside scope: check the host list afterwards. One page load per URL. |
| 6 | TLS settings | `sslscan <host>:443` or `testssl.sh <host>:443` | 🟡 | Also sends Heartbleed- and CCS-style test probes. One host at a time; never on OT; say it aloud. |
| 7 | Standard files | `curl -s http://<host>/robots.txt` and `/sitemap.xml`, `/.well-known/security.txt` | 🟢 | Single requests |
| 8 | Browse as a user | Burp Community, intercept off, browse every feature | 🟢 | Normal user traffic |
| 9 | Nmap web scripts, informational | `nmap -n -p 80,443 --script http-title,http-headers,http-methods <host>` | 🟡 | Named scripts only |
| 10 | Hidden paths | `ffuf -u http://<host>/FUZZ -w <wordlist> -rate 20 -t 5` | 🟡 | One request per word. `-rate 20 -t 5` keeps it to 20 requests per second and 5 threads. Default `-t 40` with no `-rate` is much louder. |
| 11 | Hidden paths (alternative) | `gobuster dir -u http://<host> -w <wordlist> -t 2 --delay 200ms` | 🟡 | Same idea. The delay is per thread, so `-t 2 --delay 200ms` is about 10 requests per second. |
| 12 | Subdomain/vhost check | None yet | 🟡 | Only for hostnames named in the SOW; ask the team first. Guessing names can reach outside scope: see 1.2 |

Start with a short wordlist (`common.txt`). Use a bigger one only on a claimed host, and only if the short one found something worth following.

## 4.3 Not recon: stop and ask (🔴)

| Action | Why risky |
|---|---|
| `nikto` | Thousands of requests, includes checks that can trigger bugs. One host at a time, with approval, and `-Tuning 1,2,3` to limit what it checks. |
| `sqlmap`, XSS scanners, automated fuzzers on forms | Sends attack input to the app; can write data; follows `checklists/20-web-app.md` and the ROE |
| Login brute forcing (`hydra`, `ffuf` on a login form) | Locks accounts; the ROE may bar it |
| Crawlers with no scope limit | Follow links to other sites; see 1.2 |
| Any request that submits a form, creates an account, or places an order | Changes data. Test accounts only, logged in `created-accounts-and-artifacts.csv` |
| Upload endpoints | Writes files to the server |

## 4.4 What to write down

**Per site:** URL, title, server and framework versions, TLS findings, login page present, interesting paths, screenshot filename.
- **Where:** one row per site in `hosts.csv` notes, or `field-notes/<yourname>/NOTE-web-<host>.md` when it is long.
- **Findings** (version disclosures with known issues, directory listing, exposed `.git`, missing TLS): get finding IDs immediately (R6).

## 4.5 Proxy hygiene

- Point Burp at in-scope targets only. In Burp's Target tab, set Scope to the SOW hosts and turn on "Don't send items to history/Logger if out of scope" so stray requests do not pile up.
- Save Burp requests and responses that prove a finding as evidence files (`checklists/40-evidence-and-logging.md`).

---

# Part 5: For the report writers

Recon output feeds the report's scope section, asset list, and the "how it was found" steps for findings. This part covers reading scan output and checking it is usable and in scope. No scanning needed.

## 5.1 What the scan files are

`-oA name` writes three files with the same content in three formats:

| File | Format | Use |
|---|---|---|
| `name.nmap` | Plain text, same as the screen | Read it; paste short excerpts into the report |
| `name.gnmap` | One line per host | `grep` and `awk` (the live host list is built from this) |
| `name.xml` | Structured | Feeds tools and the tracker |

## 5.2 Reading port states

| State | Means | In the report |
|---|---|---|
| `open` | A service answered | Record the port and service |
| `closed` | The host answered, nothing listening | Not a finding |
| `filtered` | No answer; a firewall may be dropping probes | Not "closed"; say "filtered" |
| `open\|filtered` | UDP, FIN, Xmas and Null scans: no reply, cannot tell | Do not call it open |
| `tcpwrapped` | Connection accepted then closed | Not a finding by itself |

A service name with a `?` (for example `ftp?`) means `-sV` ran but could not confirm the service, so nmap shows the port's usual name. Not confirmed, and not a finding until a version check confirms it.

Docs: https://nmap.org/book/port-scanning.html

## 5.3 Checks before a scan result goes into the report

| Check | Why |
|---|---|
| Every IP in the output is in `scope.txt` | Out-of-scope activity is a rules problem (rulebook p4); tell the team now, not at report time |
| The command line at the top of the `.nmap` file is saved with the output | Reproduction steps need the exact command (R7) |
| A timestamp is on the file | Findings need when they were found |
| Output file exists (`-oA` was used) | A result with no file cannot be reproduced |
| Any 🔴 command has an approval line in `NOTE-approvals.md` | Penalty reduction in an incident depends on proof |
| OT hosts were not hit by version probes or scripts | Compare the command against `exclude.txt` |

Send back to the author anything that fails a check.

## 5.4 What the report needs from recon

| Report part | Recon source |
|---|---|
| Scope and assets table | `scope.txt`, `live.txt`, `hosts.csv` |
| Methodology | The ladder in 1.7 (what was run, in order, with ratings) |
| Finding reproduction steps | Exact command plus the relevant output lines, from the `.nmap` file |
| Incident reports | Terminal logs and scan file timestamps (rulebook p10: source and destination IPs, timeline, damage) |

## 5.5 Wording

State what was observed. "Port 445 open; SMB signing not required (`nxc smb` output below)" is a finding; "the server is vulnerable" with only an open port is not. Use "filtered" and "open" as nmap uses them.

---

# Part 6: Advanced (locked): masscan and rustscan

> 🔴 **Nobody uses these until they are comfortable with everything in Part 1.**
> - The rulebook neither bans them nor lists allowed tools (p5: teams may use "any allowed mechanisms to engage the targets, within the confines of the Scope of Work (SOW) and Rules of Engagement (ROE)").
> - Both are built for speed, and speed is the risk: a mistyped rate or range can flood a network faster than anyone can stop it. A past team's concurrent scanning harness warned in its own README about large traffic spikes.
> - Practice only in the lab (see `PRACTICE-DRILLS.md`). On the event network, either needs the whole team's agreement first.

## 6.1 masscan

Docs: https://github.com/robertdavidgraham/masscan

Sends SYN probes at very high rates from its own TCP stack. Good for finding open ports across big ranges, not for service detail.

| Flag | Rating | Notes |
|---|---|---|
| `--rate N` | 🟡 at N ≤ 100, 🔴 above | Packets per second. **Default is 100.** Never raise it in the event. |
| `-p 80,443` | 🟢 | Choose ports; keep to a short list |
| `--top-ports N` | 🟡 | Not in the masscan README: check `masscan --help` on our Kali image, and remove this row if it is missing. |
| `-e IFACE` | 🟢 | Which network interface to send from |
| `--router-mac MAC` | 🟢 | The gateway's hardware address; needed on some links (see the note below) |
| `-iL`, `--excludefile` | Required | Same scope files as nmap |
| `-oL file`, `-oX file` | 🟢 | Save output |
| `--source-port N` | 🔴 | Send from a fixed source port N. Used with `--banners`, together with a local firewall rule that drops replies to that port. |
| `--banners` | 🔴 | Completes connections; interacts with services. Needs `--source-port` and a local firewall rule, because masscan uses its own network stack and the operating system otherwise resets the connection. |

Check `-iL` and the other flags against `masscan --help` on our Kali image before use.

Safe use: `sudo masscan -iL scope.txt --excludefile exclude.txt -p 22,80,443,445 --rate 100 -oL mass.txt`

masscan can fail on VPN links, which have no gateway hardware address, and needs `-e` and `--router-mac` there. Test over the same link (VPN or direct) in the lab first.

Then hand the open ports to nmap for the detail (ladder steps 5 to 8).

## 6.2 rustscan

Docs: https://github.com/RustScan/RustScan

Finds open ports fast. By default it then runs nmap on the ports it finds, so rate that step like nmap; `--scripts none` turns the hand-off off.

| Flag | Rating | Notes |
|---|---|---|
| `-a <target>` | 🟢 | One host; do not pass a big range |
| `-b N` (batch size) | 🟡 at low N, 🔴 high | Connections attempted at once. The default is large; set it low (for example `-b 100`). |
| `-t N` (timeout, ms) | 🟢 | How long to wait for an answer, in milliseconds |
| `--scripts none` | 🟢 | Do not run nmap on the open ports |
| `--ulimit N` | 🟡 | Raises the open-file limit; combined with a big batch it opens thousands of connections |
| `-- -sV` (args after `--` pass to nmap) | 🟡 | Same ratings as nmap |

Flag letters and defaults differ between RustScan versions: check `rustscan --help` on our Kali image before using any of this.

Safe use: `rustscan -a <claimed-host> -b 100 -t 3000 --scripts none`

## 6.3 Rules

1. Scope files only. Never type a range.
2. One claimed host or one subnet at a time.
3. Never on OT hosts or ranges.
4. Keep the rate or batch size low; wanting results sooner is not a reason to raise it.
5. Log it and say it aloud before starting.

---

# Part 7: Team recon workflow

> **Decided:** discover once, then claim by service (7.1). Where results are shared is still open ("Is shared storage or a shared document provided?", R6, R17); until it is answered, the whiteboard is the record of claims.

**Aim:** every in-scope host discovered once, every deeper scan with a named owner, no host scanned twice.

## 7.1 Discover once, then claim by service

1. **Discovery runs once** on `scope.txt` (ladder steps 0 to 5, including the one name lookup in step 4b, plus the OT-finding pass in 1.12). One person runs it while everyone else builds scope files, starts logged shells and reads the SOW.
2. **Results are shared**: `live.txt`, the top-100 port output, and the host rows for `hosts.csv` (`templates/tracker/hosts.csv`). The discovery run adds the rows with the `owner` column blank. Until storage is decided, everyone copies the rows into their own `hosts.csv`.
3. **Hosts are routed by what is open:**

| Open ports | Lane |
|---|---|
| 88, 389, 445, 3389, 5985 | Windows |
| 22, 111, 2049, 161/UDP, databases | Linux |
| 80, 443, 8080, 8443 | Web |
| OT ports | Whiteboard, then the whole team agrees who handles it |

The "Open port → next step" table in Part 8 gives each lane its first commands. A host can belong to two lanes (a Linux box running a web app). Both claim it on the whiteboard.

4. **Claim before you scan deeper.** (Where addresses come from: the box in 1.2.) Say the host aloud, write your name next to it on the whiteboard, and set `owner` in your own copy of `hosts.csv`. No claim, no scan beyond step 5.
5. **Then run your lane's ladder on your claimed hosts** (Parts 2 to 4), one host at a time.

**Cost:** about 15 minutes at the start with one scanner. Use the time for the SOW, scope files and logging.

## 7.2 Not chosen: split by subnet

Giving each pair whole subnets was considered and not chosen: the subnet with the domain controller may go to the pair that cares least about it, and hosts that belong in another lane need handing over.

## 7.3 Rules

| Rule | Mechanism |
|---|---|
| Nobody scans a host someone else owns | The whiteboard claim, checked before any scan (and the `owner` column once storage is decided) |
| Nobody scans outside `scope.txt` | `-iL scope.txt` on every command; step 0 preview |
| Broad scans go through the discovery step only | Ladder steps 6 and above are for claimed hosts only |
| Every new OT host is announced and excluded | Whiteboard and `exclude.txt` (`checklists/30-ot-ics-safe.md`) |
| Every 🟡 command is said aloud | Rating key (1.1); a short phrase is enough |
| Every 🔴 command has an approval line | `NOTE-approvals.md` (1.1) |

## 7.4 Where results go

Until the storage question is answered, results land in `~/cptc-work/field-notes/<yourname>/recon/` and in `~/cptc-work/tracker/hosts.csv`. The team README's pull list already includes `field-notes/` and `tracker/`, so teammates' recon output arrives in `~/cptc-work/incoming/<name>/` with the rest of their work.

---

# Part 8: Cheat sheets

Print one page per lane, and the Open port table in landscape.

**Ratings:** 🟢 Safe, 🟡 Noisy (say it aloud), 🔴 Risky (stop and get approval), Prohibited (never).

**Flags are explained in:** 1.6 (nmap), 2.2 (Windows tools), 3.2 (Linux tools), 4.1 (web tools) and Part 6.

## 8.1 Open port → next step

What each open port leads to after the top-100 pass and routing (Part 7). Commands are for one claimed host at a time; ratings are for in-scope IT hosts. If the host might be OT, use the slow pass from 1.12 first.

| Open port | Likely service | First command | Rating | Then | Lane |
|---|---|---|---|---|---|
| 21 | FTP | `nmap -n -p 21 --script ftp-anon <host>` | 🟡 | Version: `nmap -n -sV -p 21 <host>` | Linux |
| 22 | SSH | `ssh-audit <host>` | 🟢 | Note the banner; no login guessing | Linux |
| 25 | SMTP | `nmap -n -p 25 --script smtp-commands <host>` | 🟡 | `smtp-enum-users` is 🔴: only if the ROE allows, with an approval line | Linux |
| 53 | DNS | `dig @<host> <domain> ANY` | 🟢 | Zone transfer check (`AXFR`): 🟡 | Windows |
| 80, 8080 | Web | `httpx-toolkit -u http://<host>:<port> -title -tech-detect` | 🟢 | `whatweb`, then screenshots | Web |
| 88 | Kerberos | Mark as domain controller on the whiteboard | 🟢 | Run the 389 and 445 steps on it | Windows |
| 111, 2049 | RPC, NFS | `showmount -e <host>` | 🟢 | `rpcinfo -p <host>` | Linux |
| 135, 139, 445 | RPC, SMB | `nxc smb <host>` | 🟢 | Null-session shares and password policy (2.3): 🟡 | Windows |
| 161/UDP | SNMP | `onesixtyone -c community.txt <host>` | 🟡 | If a community answers: `snmpwalk -v2c -c <community> <host> 1.3.6.1.2.1.1` | Linux |
| 389, 636 | LDAP | `ldapsearch -x -H ldap://<host> -b "" -s base namingContexts` (`ldaps://` for 636) | 🟢 | `nxc ldap` anonymous users: 🟡 | Windows |
| 443, 8443 | HTTPS | `sslscan <host>:<port>` | 🟡 | `httpx-toolkit`, then `whatweb` | Web |
| 1433 | MSSQL | `nmap -n -p 1433 --script ms-sql-info <host>` | 🟡 | Version only | Windows |
| 3306, 5432 | MySQL, PostgreSQL | `nmap -n -sV -p <port> <host>` | 🟡 | Version only; no login attempts | Linux |
| 3389 | RDP | `nmap -n -p 3389 --script rdp-enum-encryption <host>` | 🟡 | Note whether it is exposed at all | Windows |
| 5985, 5986 | WinRM | `nxc winrm <host>` | 🟢 | Reports the service; do not log in without a credential | Windows |
| 6379 | Redis | `nc -nv <host> 6379`, then `PING` | 🟢 | No further commands | Linux |
| 102, 502, 2404, 4840, 20000, 44818, 47808/UDP | OT protocols | **Stop.** Whiteboard, `exclude.txt`, tell the team (1.4) | 🔴 | Identify with the slow, read-only checks in `checklists/30-ot-ics-safe.md` | Team decision |
| Anything else | Unknown | `nmap -n -sV -p <port> <host>` | 🟡 | Search the service name and version | Whoever claimed it |

## 8.2 Everyone

| Do | Command |
|---|---|
| List targets only | `nmap -sL -n -iL scope.txt --excludefile exclude.txt` 🟢 |
| Names, once (the only scan without `-n`) | `nmap -sL -iL live.txt --excludefile exclude.txt -oN names.txt` 🟢 |
| Ping sweep | `sudo nmap -n -sn -PE -iL scope.txt --excludefile exclude.txt -oA disc-icmp` 🟢 |
| Top 100 ports, capped | `nmap -n --top-ports 100 --max-rate 100 --exclude-ports <OT-string> -iL live.txt --excludefile exclude.txt -oA top100` 🟢 |
| One host, all TCP (claimed hosts only) | `nmap -n -p- --max-rate 300 --exclude-ports <OT-string> <host> -oA full-<host>` 🟡 |
| Versions on open ports (claimed hosts only) | `nmap -n -sV -p <ports> <host>` 🟡, 🔴 on OT |
| Slow OT port check (confirm the ROE first, tell the team) | `nmap -n -sT -p 102,502,2404,4840,20000,44818 --max-rate 10 --max-retries 1 -iL ot-ranges.txt --excludefile exclude.txt -oA ot-find` 🟡 |
| Before scanning | `ip a`, `ip r`, `cat /etc/resolv.conf`, then listen with `tcpdump` (1.9) 🟢 |
| Always | `-n`, `-oA`, `-iL scope.txt`, `--excludefile exclude.txt`. `<OT-string>` is the full port list in 1.5. |
| Never | `-T5`, `-A`, `vuln`/`brute`/`intrusive` scripts, typed ranges |
| Watch | `--stats-every 30s`; after: repeat the ping sweep and `ndiff disc-icmp.xml after-<HHMM>.xml` (1.10) |
| Stop | Ctrl-C, say it aloud, note the time, follow 1.3 |

## 8.3 Windows / AD

| Goal | Command |
|---|---|
| Windows ports | `nmap -n -sT -p 53,88,135,139,389,445,636,1433,3389,5985 <host>` 🟢 |
| Name, domain, signing | `nxc smb <claimed-hosts>` 🟢 |
| Null-session shares | `nxc smb <dc> -u '' -p '' --shares` 🟡 |
| Password policy | `nxc smb <dc> -u '' -p '' --pass-pol` 🟡 |
| Anonymous LDAP | `ldapsearch -x -H ldap://<dc> -b "" -s base namingContexts` 🟢 |
| Everything on one host | `enum4linux-ng -A <host>` 🟡 |
| Never without approval | Password guessing, brute scripts, poisoning |

## 8.4 Linux

| Goal | Command |
|---|---|
| Linux ports | `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` 🟢 |
| SSH audit | `ssh-audit <host>` 🟢 |
| NFS exports | `showmount -e <host>` 🟢 |
| SNMP system info | `snmpwalk -v2c -c public <host> 1.3.6.1.2.1.1` 🟢 |
| Community guess | `onesixtyone -c community.txt <host>` 🟡 |
| Anonymous FTP | `nmap -n -p 21 --script ftp-anon <host>` 🟡 |
| Never without approval | Login guessing, mounting writable, `snmpset` |

## 8.5 Web

| Goal | Command |
|---|---|
| Web ports | `nmap -n -sT -p 80,443,8000,8008,8080,8081,8443,8888,9000 <host>` 🟢 |
| What responds | `httpx-toolkit -l urls.txt -title -status-code -tech-detect -rate-limit 10 -duc` 🟢 |
| Fingerprint | `whatweb http://<host>:<port>` 🟢 |
| TLS | `sslscan <host>:443` 🟡 (also sends test probes) |
| Screenshots | `gowitness scan file -f urls.txt` 🟢 |
| Hidden paths | `ffuf -u http://<host>/FUZZ -w <list> -rate 20 -t 5` 🟡 |
| Never without approval | `nikto`, `sqlmap`, login brute force, forms and uploads |

---

# Glossary

| Term | Meaning |
|---|---|
| SOW | Scope of Work: the officials' list of targets we may test |
| ROE | Rules of Engagement: how we may test |
| OT | Operational technology: industrial and ride control systems |
| Discovery | Finding which hosts are up |
| Enumeration | Listing what a host offers: services, versions, shares, users |
| Banner | The text a service shows when you connect |
| Null session | A connection with an empty username and password |
| Lane | One of the three work groups: Windows/AD, Linux, Web |
| `live.txt` | The file of hosts that answered discovery (1.7, step 4) |
| DC | Domain controller: the server that handles logins for a Windows domain |
| CIDR | Address range written with a slash, for example `10.0.5.0/24` |
| NSE | Nmap Scripting Engine: the scripts run with `--script` |
| IDS | Intrusion detection system: software that raises alerts on suspicious traffic |
| MIB / OID | SNMP's names and numbers for the items a device reports |
| vhost | One of several websites served from the same address |
| Operations | The competition's Operations Team (R12) |
| Finding ID | The identifier given to a finding the moment it is found (R6) |
| Rate | Packets or requests sent per second |
| `-oA` | Save nmap output in all three formats |
| Claimed host | A host you have said aloud and written your name next to on the whiteboard; also set as `owner` in your copy of `hosts.csv` |

**Official documentation**

| Tool | Link |
|---|---|
| nmap | https://nmap.org/book/man.html and https://nmap.org/nsedoc/ |
| NetExec | https://www.netexec.wiki/ |
| enum4linux-ng | https://github.com/cddmp/enum4linux-ng |
| ssh-audit | https://github.com/jtesta/ssh-audit |
| httpx | https://github.com/projectdiscovery/httpx |
| ffuf | https://github.com/ffuf/ffuf |
| Burp Community | https://portswigger.net/burp/documentation |
| masscan | https://github.com/robertdavidgraham/masscan |
| rustscan | https://github.com/RustScan/RustScan |
