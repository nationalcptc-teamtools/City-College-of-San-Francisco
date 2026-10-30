*Draft: commands copied from 2024, not yet checked.*

# 8. HSTS Not Enabled

- **Phase:** No credentials
- **Risk:** 🟢 Safe: one request, reading the response headers.
- **Tier:** Recognize
- **Finding:** library L21 (`cleartext-protocols`)
- **Ports:** 443
- **Tools:** curl or PowerShell, Burp Suite
- **You need:** nothing

## What it is
The `Strict-Transport-Security` header tells browsers to use only HTTPS with a site. Without it, a user can be pushed onto unencrypted HTTP (a downgrade attack) and have traffic read.

A low-severity finding, often reported together with #10 and #11.

**Fix to recommend:** send the header on every HTTPS response.

## Commands
Linux:

1. `curl -skI $URL | grep -i strict-transport-security` [[NOTE: from 2024, not yet checked]]

Windows (PowerShell):

1. `Invoke-WebRequest -Uri $URL | Select-Object -ExpandProperty Headers` [[NOTE: from 2024, not yet checked]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the response headers, with the header missing and the host visible.

## Practice
- Any HTTPS site the team runs; check its headers

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
