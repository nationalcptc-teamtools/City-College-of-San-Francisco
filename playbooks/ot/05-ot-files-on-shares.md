*Draft, needs review.*

# 5. OT Files Stored on Office Shares

- **Phase:** Discovery (IT side)
- **Risk:** 🟢 Safe / 🔴 Risky / Prohibited: read-only listing and copying of in-scope files are Safe; opening a project in software that may connect to an HMI/controller is Risky—**ask the client contact in writing first, every time**; uploading a project or anything that could stop or damage a process without permission is Prohibited
- **Tier:** Recognize *(proposed)*
- **Finding:** none in the library yet; related library L18 (`ot-network-segmentation`) when the files reveal or enable an IT-to-OT path
- **Runs on:** SMB/NFS shares, collaboration folders, engineering workstations, document repositories and backup locations
- **Ports:** ordinary approved IT file-sharing ports; do not scan controllers to find the files
- **Tools:** the team's approved read-only file-share workflow; text or archive viewers that cannot contact live equipment

## What it is
Office shares may hold ladder-logic projects, HMI projects, controller backups, vendor manuals, network diagrams and configuration exports. They can reveal device addresses, tags, register maps, credentials, firmware and the software needed to administer operations.

Past CPTC environments contained PLC firmware and configuration, HMI-to-controller identifiers, and publicly exposed grid diagrams. The OT / ICS Safe-Testing Sheet (`checklists/30-ot-ics-safe.md`) therefore starts OT discovery on the IT side (shares, project files, ladder-logic backups, vendor documentation) before touching a suspected controller.

Report the exposure without loading a project into engineering software. Some engineering tools connect automatically to the last configured device, so opening a file in the wrong tool can become active OT interaction.

## Commands

For every broad scan of a range that might contain OT, use the checklist's brittle-port exclusion exactly:

```text
--exclude-ports T:102,502,789,1089-1091,1883,1911,1962,2404,2455,4000,4840,4911,5006-5007,5094,8883,9600,18245-18246,20000,34962-34964,44818,48898,U:1089-1091,2222,4000,9600,20000,34962-34964,34980,44818,47808,48899
```

1. Use IT-side hostnames, DNS, directory objects and already approved share discovery to locate likely engineering or operations folders.
   Expected: In-scope share names or paths that suggest controls, engineering, PLC, HMI, SCADA, backups, projects, vendors or configuration.
2. [[TODO: Insert the team's approved read-only share-enumeration command from an existing IT playbook; it must not mount read-write, upload, rename or delete anything.]]
   Expected: A directory listing obtained with the tester's existing authorization.
3. Record filenames, extensions, dates, sizes and permissions. Copy only the minimum in-scope evidence needed; do not launch macros or vendor engineering software.
   Expected: Evidence identifies the exposed OT material and who can read it without changing the source.
4. Review safe text, PDF or archive metadata offline. Treat live project formats as data, not something to deploy or open in a connected engineering suite.
   Expected: Device names, network information or project purpose can be documented without contacting OT.
5. Stop before opening any project in software that might connect to a live HMI or controller. That is 🔴 Risky: **ask the client contact in writing first, every time**. Uploading or applying a configuration without permission is Prohibited.
   Expected: Exposure is proven entirely from the office share.

## Evidence to capture
- `evidence/F-NNN-01.png`: the share path, relevant filenames and permissions; redact credentials and sensitive operational values.
- `evidence/F-NNN-02.txt`: a read-only directory listing with timestamp.
- File hashes for any evidence copy, plus the original path and access identity.
- If the files document a route from IT to live OT, cross-reference library L18 (`ot-network-segmentation`).

## Practice
- [[TODO: Create a harmless sample share with representative project backups, manuals and configuration exports, then verify the review tools cannot contact a controller.]]
- Practise recognizing common control-project artifacts without opening them in live engineering software.

---
*Written by the CCSF 2026 team from the OT/ICS safe-testing checklist and past-CPTC environment research.*
