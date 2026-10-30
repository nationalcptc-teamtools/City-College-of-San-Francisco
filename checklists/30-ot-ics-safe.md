# OT / ICS (Rides) Safe-Testing Sheet

> Treat ride control as **safety-critical**. In real OT work, the deliverable is mostly **finding and reporting exposure**, not exploitation. Breaking a ride is the fastest way to lose points and to need an incident report.

## Before touching anything
> **Rule R11:** OT may or may not be in scope; the SOW decides. Identifying OT is fine (this sheet). Anything that writes, sends a command or could disrupt a process is 🔴 Risky: ask the client contact in writing first, every time, and log the answer.

- [ ] Re-read the ROE for OT. Is active testing allowed at all? Which hosts? (playbook: playbooks/general/03-unfamiliar-business-systems.md)
- [ ] Tell the team before any traffic to suspected OT ranges
- [ ] If anything is unclear, **ask Operations first**

## Identify (low impact)
- [ ] Find OT from the IT side first: hostnames, DNS, AD objects, shares (HMI project files, ladder logic backups, vendor docs) · 🟢 Safe / 🔴 Risky / Prohibited (playbook: playbooks/ot/05-ot-files-on-shares.md)
- [ ] Common ports to recognize: 502 (Modbus/TCP), 102 (S7comm), 44818 / UDP 2222 (EtherNet/IP), 20000 (DNP3), 47808/UDP (BACnet), plus VNC and web UIs on HMIs · 🟢 Safe / 🔴 Risky / Prohibited (playbooks: playbooks/ot/01-unauthenticated-hmi.md, playbooks/ot/02-default-hmi-passwords.md)
- [ ] If scanning is allowed: **TCP connect, specific ports, slow**, e.g. `nmap -sT -Pn -p 502,102,44818 --max-rate 10 <host>`. No `-A`, no version-intensity sweeps, no UDP floods (a single UDP identification request to one host, as in the steps below, is fine). Slowest pace (from last year's notes): add `--scan-delay 1s --max-parallelism 1`. · 🟢 Safe / 🔴 Risky / Prohibited (playbook: playbooks/ot/04-it-to-ot-reachability.md)
- [ ] Read-only identification only if allowed, e.g. `nmap -sT -p 502 --script modbus-discover <host>` (one host at a time). Never add `modbus-discover.aggressive=true`: it walks every unit ID instead of sending one request. · 🟢 Safe / 🔴 Risky / Prohibited (playbook: playbooks/ot/03-unauthenticated-controllers.md)
- [ ] Other protocols, same rules (only if allowed, one host at a time, one read-only identification request each; from last year's notes) · 🟢 Safe / 🔴 Risky / Prohibited (playbook: playbooks/ot/03-unauthenticated-controllers.md):
  BACnet `nmap -Pn -sU -p 47808 --script bacnet-info <host>` ·
  EtherNet/IP `nmap -Pn -sU -p 44818 --script enip-info <host>` ·
  Niagara Fox `nmap -Pn -sT -p 1911,4911 --script fox-info <host>` ·
  PCWorx `nmap -Pn -sT -p 1962 --script pcworx-info <host>`

## Brittle ports: exclude from every broad or aggressive scan
Many controllers crash or misbehave when version detection or scripts hit their industrial service. Add this exclusion to **every** broad `nmap` scan on any range that might hold OT:

```
--exclude-ports T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

| Port(s) | Protocol |
|---|---|
| TCP 102 | Siemens S7comm (ISO-TSAP) |
| TCP 502 | Modbus/TCP |
| TCP 789 | Red Lion Crimson |
| TCP/UDP 1089–1091 | Foundation Fieldbus HSE |
| TCP 1883, 8883 | MQTT (plain / TLS) |
| TCP 1911, 4911 | Niagara Fox (building automation) |
| TCP 1962 | PCWorx (Phoenix Contact) |
| TCP 2404 | IEC 60870-5-104 |
| TCP 2455 | CODESYS |
| TCP/UDP 4000 | Emerson ROC Plus |
| TCP 4840 | OPC UA |
| TCP 5006–5007 | Mitsubishi MELSEC |
| TCP 5094 | HART-IP |
| TCP/UDP 9600 | Omron FINS |
| TCP 18245–18246 | GE SRTP |
| TCP/UDP 20000 | DNP3 |
| TCP/UDP 34962–34964 | PROFINET |
| UDP 34980 | EtherCAT |
| TCP/UDP 44818, UDP 2222 | EtherNet/IP (Rockwell / Allen-Bradley) |
| TCP 48898, UDP 48899 | Beckhoff ADS/AMS |
| UDP 47808 | BACnet/IP |

- **The port list is a safety net, not a guarantee.** Some devices fall over from plain host discovery. As soon as you identify an OT host, tell the team aloud, write it on the whiteboard, and add it to `exclude.txt` with a `# OT` tag, for example `10.0.5.20  # OT` (everyone appends it to their own copy; no tool shares the file. **TBD:** blocked by the open question "Is shared storage or a shared document provided?"). Use `--excludefile exclude.txt` on all broad scans. From then on, touch it only with the low-rate checks above.
- The list was built from a public CPTC team's scan-exclusion list plus other common ICS ports. Add anything the scope document names.

## Never (unless the ROE explicitly says otherwise, in writing)
- Write coils or registers, change setpoints, upload or download PLC programs, or put a PLC in stop or program mode
- Run vulnerability scanners or fuzzers against controllers
- Brute force HMI logins

## What makes a strong OT finding
- **Reachability:** "From the guest Wi-Fi / corporate LAN, an attacker can reach the ride control network" (segmentation failure) (playbook: playbooks/ot/04-it-to-ot-reachability.md)
- Default or shared credentials on HMIs and engineering workstations (playbook: playbooks/ot/02-default-hmi-passwords.md)
- Unauthenticated industrial protocols exposed beyond the control network (playbook: playbooks/ot/03-unauthenticated-controllers.md)
- Engineering workstations joined to the corporate domain with paths from compromised users
- Impact written in **safety and operational** terms, with remediation following IEC 62443 zones and conduits
