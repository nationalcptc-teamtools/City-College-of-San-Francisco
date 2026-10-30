# Severity Guide

Rate with **CVSS 3.1 for the technical score**, then adjust the reported severity for **business context**, and write down why. Judges reward consistent, justified ratings more than high ones.

| Severity | CVSS | Typical examples |
|---|---|---|
| Critical | 9.0–10.0 | Domain Admin compromise; ESC1-vulnerable certificate template (it leads to domain admin); unauthenticated RCE on an internet-facing host; demonstrated ability to change ride or PLC state; bulk cardholder data exposure |
| High | 7.0–8.9 | Authenticated RCE; crackable Kerberoastable service account with admin rights; SQLi exposing guest PII; ride-control network reachable but not changed |
| Medium | 4.0–6.9 | SMB signing not required (relay possible); IDOR exposing other guests' tickets; weak password policy |
| Low | 0.1–3.9 | Verbose errors; missing security headers with no demonstrated impact |
| Informational | — | Hardening advice, positive observations |

## Rules
1. **One CVSS version, 3.1, for every finding.** Two CPTC10 finalists mixed versions within one report, and it reads as careless.
2. **Rate what we demonstrated, not what is theoretically possible.** Every finding gets a one-line "Why this severity" on its `Why this severity` line.
3. **Hygiene items default to Low or Informational** unless we demonstrated impact. That covers missing headers, verbose errors, policy recommendations with no demonstrated weakness and broken functionality. (A weak password policy we actually exploited, e.g. by spraying, is Medium, as in the table.) Inflating them costs credibility; CPTC10 judges praised a team for downplaying insignificant issues.
4. **Always write severity as a word.** Color is a supplement and never carries the meaning alone.

## Context adjustments (state them in the finding)
- **Raise** for guest physical safety (rides) and payment data (PCI DSS).
- **Chains don't change a finding's rating.** Rate each finding on its own demonstrated impact. When several findings together reach something worse (a path to Domain Admin, say), add one chain finding that describes the whole path and rates it on the end result: L13 (Critical) when the path reached Domain Admin, L07 (High) for a path that stopped short. Choke points (the one fix that breaks the path) set remediation priority in the roadmap, not severity.
- **Lower** when exploitation requires unlikely preconditions or we observed compensating controls.

## Calibration examples (CPTC10 finals, same environment)
| Issue | How finalists rated it | Lesson |
|---|---|---|
| Unauthenticated custom code interpreter (RCE) | Medium 4.2 up to Critical 9.8 | Part of the spread is legitimate: one team only showed a file write, while others got root. Rate what you proved, and say what you proved. |
| Brute-forceable TOTP on the web app | Critical (two teams) and Low (two teams) | Without a stated rationale the report reads as arbitrary. Write the "why". |

Library defaults in `findings-library/` are starting points; set the final rating from what you actually demonstrated.

## Consistency rule
All ratings get one review pass together, sorted by severity and checked against the calibration examples above, so the report reads as one voice.
