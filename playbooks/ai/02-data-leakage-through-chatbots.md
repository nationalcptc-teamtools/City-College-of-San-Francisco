*Draft, needs review.*

# 2. Data Leakage Through Chatbots

- **Phase:** Application testing
- **Risk:** 🟢 Safe for one read-only request using our own test data. Repeated requests are 🟡 Noisy. Testing with real users' data, broader documents or a tool action is 🔴 Risky: ask the client contact in writing first, every time, and log it.
- **Tier:** Must know
- **Finding:** no dedicated library entry; use L16 (`idor-broken-access-control`) when the root cause is missing object-level access control
- **Runs on:** chatbots and assistants connected to documents, user records, secrets or APIs
- **Tools:** Browser, Burp Suite, transcript with timestamps
- **You need:** one test account; two test accounts under our control for a cross-user check

## What it is
A chatbot leaks data when it returns information the current user should not see. The leak may come from its hidden instructions, documents, another user's records, credentials in its context or an API the chatbot can query with too much privilege.

Chatbot-specific weaknesses appeared in **one of the six reviewed CPTC environments**, the social-media scenario. Demonstrated results included chatbot information disclosure and secret exposure through crafted prompts. The business effect depends on the data: account takeover, privacy loss and abuse of a trusted platform can all start with one leaked value.

Use test accounts and test records first. If real customer or employee data begins to appear, stop, preserve the minimum evidence and notify the team.

**Checklist:** AI / LLM step 1: Map it (`checklists/60-ai-llm.md`) and step 5: Data exposure and access control (`checklists/60-ai-llm.md`). Related finding: L16 (`idor-broken-access-control`).

## Commands

1. List what the chatbot can see: documents, user data, credentials and connected services. List what it can do separately. 🟢 Safe. [[NOTE: from checklist 60]]
   Expected: The data map names each source and the role that should be allowed to reach it.
2. Ask one question about the current test user's own record. 🟢 Safe. [[NOTE: from checklist 60]]
   Expected: The chatbot returns only data the current test user can already see, or refuses.
3. With two test accounts under our control, ask the first account about one harmless record owned by the second account. 🟢 Safe. [[NOTE: from checklist 60]]
   Expected: A refusal or filtered response means the boundary held. Returning the second test account's record is evidence of broken access control.
4. Ask once whether it can search documents outside the current test role or has access to credentials, keys or connection strings. Ask about the category, not for a real value. 🟢 Safe. [[NOTE: from checklist 60]]
   Expected: The chatbot refuses or describes only allowed sources. If protected content starts to appear, stop and redact it in evidence.
5. [[TODO: Define the minimum approved request and stop condition for when two controlled test accounts are unavailable or the test could expose real user data. This is 🔴 Risky: ask the client contact in writing first, every time, and log it.]]
   Expected: Written approval names the data class, account, one request and notification path before the test runs.

## Evidence to capture

- `evidence/F-NNN-01.txt`: the full prompt and response transcript with timestamps.
- `evidence/F-NNN-02.png`: the unauthorized response, with personal data and secrets redacted.
- The data-source map and the role that should have access.
- The two test-account identifiers, or the written approval if controlled accounts were unavailable.

## Practice

- **Free, public and legal:** [PortSwigger Web Security Academy: Web LLM attacks](https://portswigger.net/web-security/llm-attacks/). Use the Academy labs and their supplied accounts.

---
*Study draft for the CCSF 2026 team.*
