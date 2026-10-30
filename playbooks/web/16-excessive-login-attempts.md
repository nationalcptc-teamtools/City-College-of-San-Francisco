*Draft: command steps not filled in yet.*

# 16. No Limit on Login Attempts

- **Phase:** No credentials
- **Risk:** 🟡 Noisy *(proposed)*: many failed logins. **Only against a test account the team controls.** Against a real user it can lock them out: 🔴 Risky.
- **Tier:** Recognize *(proposed)*
- **Finding:** library L17 (`web-authentication-weakness`) *(proposed)*
- **Ports:** 80, 443
- **Tools:** Burp Suite (Intruder) or a similar login tester
- **You need:** a test account whose password we know

## What it is
The login page never locks the account, slows down or blocks the sender after many wrong passwords, so an attacker can keep guessing.

In 2024: 100 wrong passwords, then the right one, and the login worked. A CAPTCHA appeared after 15 tries but accepted any answer.

**Fix to recommend:** a CAPTCHA or lockout after 3–10 failures, and blocking addresses with many failures per hour. The 2024 doc explains the thresholds; keep that text for the report.

## Commands
[[TODO: Copy the steps from the 2024 doc "Web - Excessive Login Attempts.docx". Leave out the 2024 hosts, IPs, URLs, company names and screenshots; use placeholders such as `$TARGET` and `$URL`. Format per `templates/finding.md`: numbered steps, exact command or browser step in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: the attempt count with no lockout.
- `evidence/F-NNN-02.png`: the correct password still accepted afterwards.

## Practice
- PortSwigger Web Security Academy, authentication (brute-force) labs *(proposed)*

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
