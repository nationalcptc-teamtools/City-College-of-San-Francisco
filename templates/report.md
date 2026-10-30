# Penetration Test Report: [[CLIENT_NAME]]

[[NOTE: Copy this file once, at the midpoint, to ~/cptc-work/report.md (not into findings/). Before every submission, run checklists/50-report-qa.md. Marker key: templates/README.md. Delete this line once QA passes.]]

**Prepared by:** [[FIRM_NAME]] [[NOTE: Use the firm name only, with no school identifiers.]]

**Engagement window:** [[ENGAGEMENT_START]] – [[ENGAGEMENT_END]]

**Report date:** [[REPORT_DATE]] | **Version:** [[VERSION]] | **Classification:** Confidential, prepared for [[CLIENT_NAME]]

---

## Table of Contents
[[NOTE: Generate the TOC at export time, then click every entry in the exported PDF to confirm the links work.]]

## 1. Executive Summary
[[NOTE: One page, placed directly after the TOC. Write it last, for the board rather than for engineers: no tool names, commands or CVE numbers.]]

**Overall risk: [[CHOOSE: Critical / High / Medium / Low]].** [[OVERALL_RISK_REASON]] [[NOTE: One sentence, e.g. "An attacker on the guest Wi-Fi could reach ride control systems within four hours."]]

| Critical | High | Medium | Low | Informational | Total |
|---|---|---|---|---|---|
| [[N_CRITICAL]] | [[N_HIGH]] | [[N_MEDIUM]] | [[N_LOW]] | [[N_INFO]] | [[N_TOTAL]] |

[[NOTE: Fill every column, writing 0 where there are none. These counts must match the Findings Summary table.]]

**Scope:** [[SCOPE_ONE_LINE]]

**Top risks**
1. [[RISK_IN_BUSINESS_TERMS]] ([[FINDING_ID]])
2. [[RISK_IN_BUSINESS_TERMS]] ([[FINDING_ID]])
3. [[RISK_IN_BUSINESS_TERMS]] ([[FINDING_ID]])

**What's working:** [[STRENGTHS]] [[NOTE: Genuine positives the client should keep doing.]]

**Top fixes:** [[TOP_FIXES]] [[NOTE: Prioritized, each marked as a quick win or a project.]]

## 2. Scope and Risk Method
- **In scope:** [[IN_SCOPE]] [[NOTE: List every asset class given in the scope document exactly as given: networks, web apps, cloud, AI systems, and social-engineering targets.]]
- **Out of scope:** [[OUT_OF_SCOPE]]
- **Rules of engagement we followed:** [[ROE_CONSTRAINTS]]
- **How we rate risk:** CVSS 3.1 base score, adjusted for business context, with the reason stated in each finding. Details are in Appendix A.
- **Limitations:** [[LIMITATIONS]] [[NOTE: Time, access, and any systems we deliberately didn't test, with the reason.]]

## 3. Findings Summary

| ID | Title | Severity | Affected assets | Status |
|---|---|---|---|---|
| [[FINDING_ID]] | [[FINDING_TITLE]] | [[CHOOSE: Critical / High / Medium / Low / Informational]] | [[HOST]] | [[CHOOSE: Confirmed / Exploited / Suspected]] |

[[NOTE: Order rows by severity. Use the same IDs, titles and severity words as Section 5.]]

## 4. Attack Path
[[ATTACK_PATH_DIAGRAM]] [[NOTE: One page. A diagram from our starting position to the deepest access, with finding IDs on the arrows. Mark the choke points: the fixes that break the most paths.]]

[[ATTACK_PATH_SUMMARY]] [[NOTE: Half a page at most. The full chronological narrative goes in Appendix B. If findings combine into a path, point to the chain finding here.]]

## 5. Detailed Findings
[[NOTE: Paste each finished findings/F-XXX file here, ordered by severity.]]

## 6. Remediation Roadmap
| Priority | Action | Findings addressed | Effort | Owner (suggested) |
|---|---|---|---|---|
| Immediate (0–7 days) | [[ACTION]] | [[FINDING_ID]] | [[CHOOSE: Low / Medium / High]] | [[OWNER]] |
| Short term (30 days) | [[ACTION]] | [[FINDING_ID]] | [[CHOOSE: Low / Medium / High]] | [[OWNER]] |
| Strategic (90+ days) | [[ACTION]] | [[FINDING_ID]] | [[CHOOSE: Low / Medium / High]] | [[OWNER]] |

## 7. Incident and Client Interaction Log
| Time | Type | Summary | Reference |
|---|---|---|---|
| [[INTERACTION_TIME]] | [[CHOOSE: Incident / Inject / Status update / Client request]] | [[INTERACTION_SUMMARY]] | [[REFERENCE]] |

[[NOTE: Log every incident report, inject, status update and client request, with times. Owning these openly reads as professional, and client communication is scored.]]

## Appendices
- **A. Methodology and risk rating:** [[METHODOLOGY]] [[NOTE: Our approach (PTES or NIST SP 800-115 phases) and the full severity method from templates/severity-guide.md.]]
- **B. Full attack narrative:** [[NARRATIVE]] [[NOTE: Chronological, with times, referencing finding IDs.]]
- **C. Hosts and services discovered:** [[HOST_INVENTORY]]
- **D. Tools used:** [[TOOLS]] [[NOTE: Name, version and purpose for each tool.]]
- **E. Credentials obtained:** [[CREDENTIALS]] [[NOTE: Redacted. Say where they were stored and that they were destroyed.]]
- **F. Artifacts and changes on systems:** [[ARTIFACTS]] [[NOTE: Host, what we changed or dropped, SHA-256 for any file, time created, and cleanup status.]]
