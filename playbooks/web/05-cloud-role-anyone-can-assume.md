*Draft: command steps not filled in yet.*

# 5. Cloud Role Any User Can Assume

- **Phase:** Low credentials (any cloud account in the client's environment)
- **Risk:** 🟢 Safe: listing and reading with a role the client's setup hands to anyone. Download one sample item only, and redact it.
- **Tier:** Recognize
- **Finding:** library L07 (`excessive-privilege-attack-path`)
- **Ports:** 443
- **Tools:** AWS CLI
- **You need:** any cloud credential in the client's account

## What it is
In cloud accounts, users take on **roles** to get extra rights. In 2024 any user in the account could take one development role, which could list and download every customer boarding pass. The client's staff said outsiders had already used it.

**Fix to recommend:** limit who may assume the role (least privilege).

## Commands
**Methodology:** 
- **Find something open** Gaining access to an astores!
- **Assume the role** of a privledged person.
- **Take a look around** - youre privledged now, go into privledged places.

## Evidence to capture
- `evidence/F-NNN-01.png`: assuming the role.
- `evidence/F-NNN-02.png`: the bucket listing.
- `evidence/F-NNN-03.png`: one sample item, personal data redacted.

## Practice
- [[TODO: none in the 2024 doc; add a cloud lab or local setup]]

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
