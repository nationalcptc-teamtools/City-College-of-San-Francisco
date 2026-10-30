*Draft, needs review.*

# 20. Password Reset Flow Weaknesses

- **Phase:** No credentials
- **Risk:** 🟡 Noisy: requesting a reset for our own test account (it sends an email and makes a token). 🔴 Risky: anything that could reset or lock a real user's account. Ask the client contact in writing first, every time, and log it.
- **Tier:** Recognize
- **Finding:** library L17 (`web-authentication-weakness`)
- **Ports:** 80, 443
- **Tools:** Burp Suite, a browser
- **You need:** a test account whose email inbox we can read

## What it is
"Forgot password" is a second login page, and often a weaker one. What to look for:

- **Predictable tokens:** short, sequential, time-based, or the same each time.
- **Reusable tokens:** the link still works after it's used, or never expires.
- **Host header injection:** the reset email builds its link from the request's `Host` header, so an attacker can point the link at their own server.
- **Different answers** for real and fake accounts (that part is #15).

**How often:** broken reset or account-recovery flows appeared in two of the six recent CPTC environments we reviewed, each time leading to account takeover.

⚠️ **Our own test account only.**
- Never request a reset for a real user.
- A reset can lock someone out mid-competition.

**Fix to recommend:** long random single-use tokens with a short expiry; build reset links from a fixed server setting, not the request; the same message for every address.

**Pattern: reset your own account, read the token, compare.**

**Checklist:** `checklists/20-web-app.md` (Authentication and sessions: Password reset flow).

## Commands
1. Browse the reset flow as a normal user through Burp, intercept off. 🟢 [[NOTE: from the Recon Field Guide]]
   Expected: the reset request and the email link are in Burp's history.
2. [[TODO: Add the token checks (request two resets for our test account, compare the tokens, use one twice, wait past expiry). Each request is 🟡 Noisy. Our own test account only.]]
   Expected: tokens are long, random, single-use and expire; anything else is a finding.
3. [[TODO: Add the host header check against our own test account only. Pointing a real user's link elsewhere is 🔴 Risky: ask the client contact in writing first, every time, and log it.]]
   Expected: the reset link uses the real site name whatever the `Host` header says; otherwise it's a finding.

## Evidence to capture
- `evidence/F-NNN-01.png`: the two tokens side by side (or the reused token accepted), redacted after the first and last characters.
- The test account used and the times of each request.
- For host header injection: the request and the resulting email link.

## Practice
- PortSwigger Web Security Academy, authentication labs (password reset).

---
*Written by the CCSF 2026 team from past-CPTC environment research.*
