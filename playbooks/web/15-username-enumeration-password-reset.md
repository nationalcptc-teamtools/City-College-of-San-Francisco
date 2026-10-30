*Draft: command steps not filled in yet.*

# 15. Username Enumeration via Password Reset

- **Phase:** No credentials
- **Risk:** 🟡 Noisy: each try may send a reset email to a real person. Test with one account the team controls and one made-up name; never run a list.
- **Tier:** Recognize
- **Finding:** library L17 (`web-authentication-weakness`)
- **Ports:** 80, 443
- **Tools:** Browser, Burp Suite
- **You need:** one valid username or email (ours, if we have one) and one made-up one

## What it is
The password-reset page answers differently for real and fake accounts. An attacker can use that to build a list of valid users to guess passwords against (#16).

**Fix to recommend:** the same message whether the account exists or not.

## Commands
[[TODO: Copy the steps from the 2024 doc "Web - Username Enumeration via Password Reset.docx". Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the response for the real account.
- `evidence/F-NNN-02.png`: the response for the made-up one, side by side if possible.

## Practice
- PortSwigger Web Security Academy, authentication labs

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
