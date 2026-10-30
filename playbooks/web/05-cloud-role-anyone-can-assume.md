*Draft: command steps not filled in yet.*

# 5. Cloud Role Any User Can Assume

- **Phase:** Low credentials (any cloud account in the client's environment)
- **Risk:** 🟢 Safe *(proposed)*: listing and reading with a role the client's setup hands to anyone. Download one sample item only, and redact it.
- **Tier:** Recognize *(proposed)*
- **Finding:** library L07 (`excessive-privilege-attack-path`) *(proposed)*
- **Ports:** 443
- **Tools:** AWS CLI
- **You need:** any cloud credential in the client's account

## What it is
In cloud accounts, users take on **roles** to get extra rights. In 2024 any user in the account could take one development role, which could list and download every customer boarding pass. The client's staff said outsiders had already used it.

**Fix to recommend:** limit who may assume the role (least privilege).

## Commands
[[TODO: Copy the steps from the 2024 doc "AWS - Public S3 Bucket Arbitrary Boarding Passes.docx" (its second finding, "AWS Role Assumption"). Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: assuming the role.
- `evidence/F-NNN-02.png`: the bucket listing.
- `evidence/F-NNN-03.png`: one sample item, personal data redacted.

## Practice
- [[TODO: none in the 2024 doc; add a cloud lab or local setup]]

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
