### [[FINDING_ID]]: Sensitive Services Use Cleartext Protocols

[[NOTE: Draft, needs review before it moves out of drafts/.]]

[[NOTE: Library entry L21, to be written during study. Study day: replace every TODO marker with your own general text. Competition day: copy this file to findings/F-XXX-cleartext-protocols.md, replace FINDING_ID, fill every other marker with real evidence, and delete the NOTE markers. Marker key: templates/README.md.]]

[[NOTE: Library text is general. Check each section against what you actually found, then delete this note.]]

- **Severity:** Medium [[NOTE: Library default. Set the final rating per templates/severity-guide.md.]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** Needs a position on the network path between a user and the service, or a copy of traffic, which is possible on shared Wi-Fi, a compromised machine or a network device. Sniffing tools are free and the data is readable as-is.
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-319, ATT&CK T1040, https://owasp.org/Top10/A02_2021-Cryptographic_Failures/

#### Summary
Some services send logins and data across the network in plain text instead of encrypted. Anyone who can watch the network can read user names, passwords and content, and the same passwords may work elsewhere.

#### Business impact
Captured logins and data can be used to sign in as staff or customers and reach sensitive records. Regulations often require sensitive data to be encrypted in transit. [[CLIENT_SPECIFIC_IMPACT]] [[NOTE: On the day, add one line in the client's own terms (rides, ticketing, guest data, payments).]]

#### Technical detail
Older protocols such as Telnet, FTP, HTTP, plain LDAP, SNMPv1/2c and POP3 do not encrypt traffic, so anything sent, including passwords, can be read by a device on the path. Root cause: legacy services left enabled, or services configured without TLS.

#### Reproduction steps
1. Identify services using clear-text protocols (for example by scanning for known ports and noting banners).
   Expected: A list of hosts and ports.
2. Where permitted, capture a short sample of traffic for a test login and show the user name is visible.
   Expected: Readable user name in the capture. Mask the password in evidence.
3. Note whether an encrypted version of the service is available on the same host.
   Expected: Alternative secure port listed.

(Steps are described in words. On the day, add the exact commands or requests you ran and the real output.)

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]

#### Remediation
- **Immediate:** Turn off clear-text services and use their encrypted versions (SSH, SFTP, HTTPS, LDAPS, SNMPv3). Redirect HTTP to HTTPS where the site is public.
- **Longer term:** Set a standard that requires encryption in transit, enforce TLS settings centrally, and scan for clear-text services regularly.
- **How to verify the fix:** Scan the hosts again to confirm the clear-text ports are closed, and test that the encrypted service works with valid certificates.

#### Detection (for the client's defenders)
Use network monitoring that flags clear-text authentication protocols, and firewall logs showing traffic to old service ports.

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]] [[NOTE: Delete this section if the finding stands alone.]]
