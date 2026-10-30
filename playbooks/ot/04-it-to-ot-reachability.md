*Draft, needs review.*

# 4. OT Reachable from the Office or IT Network

- **Phase:** Discovery and trust mapping
- **Risk:** 🟢 Safe / 🔴 Risky / Prohibited: slow port reachability checks are Safe; logging in or sending any direct protocol request or controller command is Risky—**ask the client contact in writing first, every time**; anything that could stop or damage a process without permission is Prohibited
- **Tier:** Must know *(proposed)*
- **Finding:** library L18 (`ot-network-segmentation`)
- **Runs on:** routes and firewall paths between corporate, guest, development, vendor and control networks
- **Ports:** recognized HMI and industrial ports from the scope and safe-testing sheet
- **Tools:** nmap, limited to slow TCP-connect and approved read-only identification

## What it is
Segmentation should stop an ordinary office compromise from reaching systems that control physical operations. A different subnet name doesn't prove isolation; check whether traffic actually crosses the boundary.

Past CPTC environments repeatedly showed this failure. In a utilities scenario, a corporate foothold reached a dam HMI and a Modbus controller network. In a manufacturing scenario, the common assessment position reached both business systems and the conveyor HMI/PLC. Other scenarios let guest or development access reach more trusted systems.

The finding is reachability itself. Don't prove impact by changing a controller. Follow library L18 (`ot-network-segmentation`) and the OT / ICS Safe-Testing Sheet (`checklists/30-ot-ics-safe.md`).

## Commands

For every broad scan of a range that might contain OT, use the checklist's brittle-port exclusion exactly:

```text
--exclude-ports T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

1. Record the permitted starting position: office workstation, corporate VLAN, guest network or another IT-side location.
   Expected: Evidence identifies the source zone from which the test is performed.
2. Identify likely OT hosts from IT-side hostnames, DNS, directory objects, shares and scope notes before direct contact.
   Expected: One or more candidate OT destinations and their expected roles.
3. If scanning is allowed, test only recognized TCP ports, slowly and one host at a time: `nmap -sT -Pn -p 502,102,44818 --max-rate 10 <host>`.
   Expected: A reachable industrial service from the recorded IT-side starting position demonstrates a path across the intended boundary.
4. Only after written approval for this host and request, identify Modbus on one host: `nmap -sT -p 502 --script modbus-discover <host>`. This direct protocol request is 🔴 Risky: **ask the client contact in writing first, every time**.
   Expected: Read-only device information confirms that the reachable service is industrial; no value changes.
5. Stop at reachability. Logging in to an HMI or sending any controller command is 🔴 Risky: **ask the client contact in writing first, every time**.
   Expected: Evidence supports segmentation failure without operational interaction.

## Evidence to capture
- `evidence/F-NNN-01.png`: source-zone evidence and the reachable destination/port.
- `evidence/F-NNN-02.txt`: the slow, specific-port output with timestamp.
- A small diagram showing `IT starting position -> missing/overly broad boundary -> OT host`.
- If an unauthenticated industrial protocol is also confirmed, cross-reference library L19 (`unauthenticated-industrial-protocol`) as a separate finding.

## Practice
- [[TODO: Build or select a two-zone lab with one intentionally incorrect firewall rule and define the expected blocked/allowed results.]]
- Practise proving the path from two different starting zones without scanning the entire control range.

---
*Written by the CCSF 2026 team from the OT/ICS safe-testing checklist and past-CPTC environment research.*
