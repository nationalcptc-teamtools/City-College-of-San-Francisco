### [[FINDING_ID]]: [[FINDING_TITLE]]

[[NOTE: The title says what is wrong and where, e.g. "Service account svc_backup has a crackable Kerberos password". Marker key: templates/README.md.]]

- **Severity:** [[CHOOSE: Critical / High / Medium / Low / Informational]]
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]] [[NOTE: One line on what we actually demonstrated, plus any context adjustment. See templates/severity-guide.md.]]
- **Likelihood:** [[LIKELIHOOD]] [[NOTE: One line on why exploitation is likely: who could do it, from where, and what they need. Keep this separate from impact.]]
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-[[CWE_ID]], ATT&CK [[ATTACK_TECHNIQUE_ID]], [[REFERENCE_URL]] [[NOTE: At least one vendor or standards link, on this line. ATT&CK mitigation IDs (M10xx) are optional.]]

#### Summary
[[SUMMARY]]

[[NOTE: Two or three sentences a non-technical manager can follow: what is wrong, what an attacker could do with it, and why the business should care.]]

#### Business impact
[[BUSINESS_IMPACT]]

[[NOTE: Use the client's own terms (rides, ticketing, guest data, payments). No tool names, commands or technical detail here; those belong in the next section. Be concrete and don't inflate it.]]

#### Technical detail
[[TECHNICAL_DETAIL]]

[[NOTE: How the vulnerability works and its root cause, not just the symptom.]]

#### Reproduction steps
[[NOTE: A finding without these is sent back (R7). Start from the tester's stated position and list prerequisites (e.g. "requires any domain user's credentials"). Each step gives the exact command or HTTP request and the result to expect, so the client's engineer can re-run it. Format: number every step, put the exact command or request in backticks, and put an "Expected:" line under each step. Example:
1. `nxc smb 10.0.0.5 -u guest -p ''`
   Expected: share list that includes SYSVOL]]

Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Evidence
- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]
- Log excerpt (timestamps included):

```
[[LOG_LINES_WITH_TIMESTAMPS]]
```

[[NOTE: Crop screenshots to what matters, and keep the text legible at page width. Box or arrow the key line. Redact secrets so only the first and last characters show.]]

#### Remediation
- **Immediate:** [[IMMEDIATE_FIX]] [[NOTE: The specific setting, patch version or config line.]]
- **Longer term:** [[LONG_TERM_CONTROL]] [[NOTE: The control that stops this whole class of issue.]]
- **How to verify the fix:** [[VERIFICATION_CHECK]] [[NOTE: A command or check the client can run.]]

#### Attack chain
[[PREVIOUS_FINDING_ID]] → this → [[NEXT_FINDING_ID]]

[[NOTE: If this was a step in a larger path, link the findings on either side. If it was a standalone finding, delete this section.]]
