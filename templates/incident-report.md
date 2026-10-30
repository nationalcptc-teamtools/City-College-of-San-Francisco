# Incident Report [[IR_ID]]

[[NOTE: File this as soon as you suspect impact. The rulebook says a thorough, timely incident report may reduce the penalty, and incomplete, vague or late ones earn nothing. Don't wait until you're sure.]]

- **Reported by:** [[SENDER_NAME]]
- **Reported to (Operations member):** [[OPERATIONS_CONTACT]]
- **Time detected:** [[DATE_DETECTED]] [[TIME_DETECTED]]
- **Time reported:** [[DATE_REPORTED]] [[TIME_REPORTED]]
- **Current status:** [[CHOOSE: Ongoing / Contained / Resolved]]

## What happened
[[WHAT_HAPPENED]] [[NOTE: A plain, factual sentence or two. No hedging and no blame.]]

## Source and destination
- **Source IP (our host):** [[SOURCE_IP]]
- **Destination IP / host:** [[DEST_HOST]]
- **Port / service:** [[PORT_SERVICE]]
- **Tool / command:** `[[COMMAND_OR_REQUEST]]`

## Timeline
- [[TIME_STARTED]]: Action started: `[[COMMAND_OR_REQUEST]]`
- [[TIME_IMPACT]]: First sign of impact: [[WHAT_WE_SAW]]
- [[TIME_STOPPED]]: Activity stopped
- [[TIME_OPS_NOTIFIED]]: Operations notified

## Impact
- Systems or services affected: [[AFFECTED_SYSTEMS]]
- Observed effect: [[CHOOSE: down / degraded / data changed / account locked / other]] [[OBSERVED_EFFECT_DETAIL]]
- Possible effects we can't rule out: [[POSSIBLE_EFFECTS]]

## Root cause
[[ROOT_CAUSE]] [[NOTE: Why our action caused this, e.g. the spray exceeded the lockout threshold, or the scan rate crashed the PLC's network stack.]]

## Remediation
- What we've already done: [[ACTIONS_TAKEN]]
- What we recommend Operations or the client do: [[RECOMMENDATION]]
- What we changed in our process so it doesn't happen again: [[PROCESS_CHANGE]]
