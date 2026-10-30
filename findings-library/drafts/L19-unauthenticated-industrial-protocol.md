### [[FINDING_ID]]: Industrial Protocol Accepts Unauthenticated Commands

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L19, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-unauthenticated-industrial-protocol.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** High [[NOTE: Library default. Showing that the protocol accepts unauthenticated requests (a read, or a documented write function exposed) is High. Critical needs a demonstrated change of ride or PLC state, which our own policy says needs the client's written OK (Unconfirmed: not a known rulebook rule; blocked by the OT question in OPEN-ITEMS.md). See checklists/30-ot-ics-safe.md. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs only network access to the device. Industrial protocols usually have no login, so anyone who can reach the port can send requests, and tools and documentation are public. Likelihood depends mostly on how reachable the device is (see the segmentation entry).
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-306, ATT&CK ICS T0855, https://csrc.nist.gov/pubs/sp/800/82/r3/final

#### Summary
A control device accepts instructions from any computer that can reach it, without checking who is asking. Anyone on the network could read its data and, in some cases, send commands that affect how equipment behaves.

#### Business impact
Unauthorized commands could stop equipment, change settings or hide a fault, causing downtime, equipment damage or safety risks. The impact can be much larger than in normal IT systems. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Many industrial protocols (Modbus, for example) were built for trusted closed networks and have no authentication, encryption or message signing. A device obeys valid-looking requests from any source, so reading values, and writing settings where write functions are enabled, is open to anyone with network access. Root cause: protocol design without security, combined with no network restrictions.

#### Reproduction steps
1. From the agreed position, check that the control device's protocol port is open.
   Expected: The port responds.
2. With the client's approval, send only a read request for a harmless value.
   Expected: Data returned without any login.
3. Do not send write requests unless the client approves in writing. Note from the device documentation whether write functions appear to be enabled.
   Expected: Read-only evidence.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Restrict access to the device's protocol port to named engineering and control systems with firewall rules, and turn off write functions that are not needed.
- **Longer term:** Place devices behind a segmented control network, use secure protocol versions or gateways that add authentication where the device supports them, and monitor protocol traffic.
- **How to verify the fix:** Repeat the read request from an unauthorized host; it should time out or be rejected. Review the firewall rules for the device.

#### Detection (for the client's defenders)
Use an OT network monitor to alert on protocol requests from unknown hosts, write commands outside change windows and unusual read patterns.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
