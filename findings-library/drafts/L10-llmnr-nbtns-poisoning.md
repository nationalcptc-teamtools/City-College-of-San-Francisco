### [[FINDING_ID]]: LLMNR/NBT-NS Enabled Allows Credential Capture

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L10, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-llmnr-nbtns-poisoning.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs only a position on the same local network as the victims, such as a wired port, guest wireless or a compromised workstation. Name lookups fail constantly (typos, old shares), so there is almost always something to capture. Very common in Windows networks.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-300, ATT&CK T1557.001, https://attack.mitre.org/techniques/T1557/001/

#### Summary
When Windows cannot find a computer name, it asks everyone on the local network, and any machine can answer. An attacker can answer falsely and have the user's login data sent to them, then guess it offline or pass it on to other systems.

#### Business impact
Staff login data can be captured from a simple mistyped name, and weak passwords recovered. Captured logins feed other attacks and may lead to file servers and business systems. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
If DNS has no answer, Windows falls back to Link-Local Multicast Name Resolution (LLMNR) and NetBIOS Name Service (NBT-NS), which broadcast the question and accept the first reply without verification. The attacker replies, the victim tries to log in to the attacker's machine and sends an NTLM challenge response, which can be cracked offline or relayed (see the SMB signing entry). Root cause: legacy fallback protocols left on by default.

#### Reproduction steps
1. From a host on the same network segment, listen passively for LLMNR and NBT-NS name queries.
   Expected: Queries seen from user machines, showing the protocols are enabled.
2. Where the rules of engagement allow active testing, answer one query with a test responder and note what the victim sends.
   Expected: A login attempt from the victim. Record account name and time, and keep no more captured data than needed.
3. Record which hosts or subnets sent queries.
   Expected: Affected hosts for the finding.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Disable LLMNR with the Group Policy "Turn off multicast name resolution" (Computer Configuration > Administrative Templates > Network > DNS Client). Disable NetBIOS over TCP/IP on network adapters (or through DHCP options).
- **Longer term:** Fix the causes of failed lookups (stale shortcuts, mapped drives), enforce SMB signing, restrict NTLM, and use strong passwords so captured data is not useful.
- **How to verify the fix:** On a sample machine, check that EnableMulticast is 0 in the registry or Group Policy result and NetBIOS is disabled on the adapter. Re-run passive listening; no LLMNR or NBT-NS queries should appear.

#### Detection (for the client's defenders)
Look for name-resolution replies from machines that are not DNS servers, and one host answering many LLMNR or NBT-NS queries. Network sensors that see these protocols are the best source. Also look for NTLM logons (event 4624) to unfamiliar hosts.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
