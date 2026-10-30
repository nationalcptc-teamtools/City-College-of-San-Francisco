*Draft: command steps not filled in yet.*

# 4. Public Cloud Storage Hosts an App Anyone Can Use

- **Phase:** No credentials (cloud)
- **Risk:** 🟡 Noisy *(proposed)*: viewing is 🟢 Safe, but submitting the form writes a new file to the client's storage. Submit once, with obviously fake data, and note the file it made.
- **Tier:** Recognize *(proposed)*
- **Finding:** none in the library yet
- **Ports:** 443
- **Tools:** Browser, AWS CLI
- **You need:** the storage bucket's name or URL (from recon, page source or DNS)

## What it is
In 2024 a web app hosted straight from a public cloud storage bucket (AWS S3) was open to anyone. It generated valid-looking boarding passes for any name, and its tags showed it was a development copy.

**Fix to recommend:** block public access on the bucket and grant only what each user needs (least privilege).

## Commands
[[TODO: Copy the steps from the 2024 doc "AWS - Public S3 Bucket Arbitrary Boarding Passes.docx" (its first finding). Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the public app with the bucket address visible.
- `evidence/F-NNN-02.png`: the item it generated from fake data.

## Practice
- [[TODO: none in the 2024 doc; add a cloud lab (flAWS-style) or local setup]]

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
