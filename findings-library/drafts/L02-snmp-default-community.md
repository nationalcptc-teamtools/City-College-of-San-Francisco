### [[FINDING_ID]]: SNMP Uses Default Community String

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L02, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-snmp-default-community.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Anyone with network access to the device's SNMP port (UDP 161) can try a short list of common community strings in seconds. Network devices, printers and appliances often ship with default strings that are never changed. Common on internal networks.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-1392, ATT&CK T1602.001, https://www.cisa.gov/news-events/alerts/2017/06/05/reducing-risk-snmp-abuse

#### Summary
A network device answers management requests using a well-known default "password" (community string). Anyone on the network can read details about the device and network, and if the write string is also default, could change its settings.

#### Business impact
Read access reveals network layout, device details and sometimes user names or settings, which helps an attacker plan. Write access could let an attacker change a device's configuration and disrupt or reroute traffic. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
SNMP versions 1 and 2c use a shared text string (the community string) instead of a user login, and send it unencrypted. Many devices ship with "public" for read and "private" for write. Anyone who knows the string can read the device's management data (interfaces, routing tables, software, sometimes configuration), and with a write string can change it. Root cause: default credentials on a protocol with weak authentication.

#### Reproduction steps
1. From a machine on the network, send an SNMP read request to the device using a short list of common community strings.
   Expected: The device replies when a string is accepted, with system description details.
2. Record the information returned (device type, name, version) and collect no more than needed.
   Expected: A short sample of returned data for evidence.
3. Do not attempt any change. If write access was not tested, report it as an observation.
   Expected: Read-only proof of access.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Change the community strings to long random values, or disable SNMP on devices that do not need it. Restrict SNMP to the monitoring server's address with an access list.
- **Longer term:** Move to SNMPv3 with authentication and encryption, keep management traffic on a separate management network, and include SNMP settings in the standard device build.
- **How to verify the fix:** Repeat the read request with the old default strings; the device should not reply. Check the device configuration shows SNMPv3 users only.

#### Detection (for the client's defenders)
Review SNMP authentication-failure logs and traps on the device, and network flow data for SNMP requests from hosts other than the monitoring server.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
