*Draft: command steps not filled in yet.*

# 4. Public Cloud Storage Hosts an App Anyone Can Use

- **Phase:** No credentials (cloud)
- **Risk:** 🟡 Noisy: viewing is 🟢 Safe, but submitting the form writes a new file to the client's storage. Submit once, with obviously fake data, and note the file it made.
- **Tier:** Recognize
- **Finding:** none in the library yet
- **Ports:** 443
- **Tools:** Browser, AWS CLI
- **You need:** the storage bucket's name or URL (from recon, page source or DNS)

## What it is
In 2024 a web app hosted straight from a public cloud storage bucket (AWS S3) was open to anyone. It generated valid-looking boarding passes for any name, and its tags showed it was a development copy.

**Fix to recommend:** block public access on the bucket and grant only what each user needs (least privilege).

## Commands
**Methodology:** 
- **Start with somewhere public** like a site or webapp.
- **What ** - Normal looking network requests could be unprotected from unprotected or unintended consequences.
A url `https://s3.us-east-1.amazonaws.com/rakmsbarcode2024/index.html`can be manipulated to produce a different result than intended:
`https://s3.us-east-1.amazonaws.com/rakmsbarcode2024**01111111111111111/index[.]html` - the result was presenting a form to create a file in an index instead of showing a file in an index

## Evidence to capture
- `evidence/F-NNN-01.png`: the public app with the bucket address visible.
- `evidence/F-NNN-02.png`: the item it generated from fake data.

## Practice
- [[TODO: none in the 2024 doc; add a cloud lab (flAWS-style) or local setup]]

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
