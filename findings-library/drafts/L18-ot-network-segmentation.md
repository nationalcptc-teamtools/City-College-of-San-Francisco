### [[FINDING_ID]]: Ride Control Network Reachable from Corporate/Guest Networks

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L18, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-ot-network-segmentation.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Reachability alone is High. Critical needs a demonstrated ability to change ride or PLC state, which our own policy says needs the client's written OK (Unconfirmed: not a known rulebook rule; blocked by the OT question in OPEN-ITEMS.md). See checklists/30-ot-ics-safe.md. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a foothold on any corporate or guest network that can route to the control network, such as a visitor's device or one phished laptop. Once a path exists, scanning it is simple. Common where flat networks grew without firewalls between zones.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-923, ATT&CK ICS T0846, https://csrc.nist.gov/pubs/sp/800/82/r3/final

#### Summary
Machines that control physical equipment can be reached from ordinary office or guest networks, with no strong barrier between. An attacker on the ordinary network could try to reach equipment that should be isolated.

#### Business impact
Control systems keep physical equipment running safely. A reachable control network raises the risk of downtime, damage or safety incidents, and ransomware on the office network could spread to operations. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Industrial and ride-control equipment was designed for closed networks and often has little security of its own, so its protection depends on separation. When firewall or VLAN rules between corporate, guest and control zones are missing or too open, traffic passes straight from the office side to the control side. Root cause: missing network segmentation and no controlled gateway (demilitarized zone) between zones.

#### Reproduction steps
1. From a permitted position on a corporate or guest network, use passive or light checks to see whether addresses in the control network range respond.
   Expected: Responses show the control zone is reachable. No response means it is blocked.
2. Record which services respond (names only), without sending any commands to the equipment.
   Expected: A short list of reachable hosts and ports.
3. Stop at reachability. Any further OT testing needs the client's written approval first.
   Expected: Evidence of reachability only.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Block traffic from corporate and guest networks to the control network at a firewall, allowing only the specific systems and ports needed.
- **Longer term:** Design network zones following IEC 62443 and NIST 800-82: separate zones, a monitored gateway between IT and OT, no direct internet access to control systems, and regular firewall rule reviews.
- **How to verify the fix:** Repeat the reachability test from the corporate and guest networks; there should be no response. Review the firewall rules to confirm default deny.

#### Detection (for the client's defenders)
Monitor firewall and flow logs for traffic from IT or guest networks into the control zone, and for new devices on the control network.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
