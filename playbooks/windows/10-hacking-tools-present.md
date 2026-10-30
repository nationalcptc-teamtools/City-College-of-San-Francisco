*Draft: command steps not filled in yet.*

# 10. Indicators of Compromise: Hacking Tools Present

- **Phase:** Low credentials (manual check over RDP or a shell)
- **Risk:** 🟢 Safe *(proposed)*: looking only
- **Tier:** Reference *(proposed)*
- **Finding:** none in the library yet
- **Runs on:** any Windows host
- **You need:** a shell or RDP login. Admin or SYSTEM sees more; a low-privileged user can do shallower checks.

## What it is
Attack tools left on a client machine are **indicators of compromise (IOCs)**. They may come from a real intrusion or from testers who didn't clean up. Either way, the client needs to know.

Don't confuse them with our own tools. Record what we drop on any host so the report can tell ours from what was already there (`checklists/10-ad-internal.md`: "Record every change you make").

## Commands
[[TODO: Copy the checks from the 2024 doc "10. Windows (any, low creds) - IOC Hacking Tools Present.docx". Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the file listing showing the tool, its path and timestamps.
- Note the host, the path and the file's timestamps in the finding.

## Practice
- [[TODO: none in the 2024 doc; a local Windows VM with a sample tool copied in works]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
