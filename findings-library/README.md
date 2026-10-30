# Findings Library

Finished, pre-written findings, so on the day we fill in specifics instead of writing from scratch.

**The 22 unfinished entries are public drafts in `findings-library/drafts/`.** When an entry is finished, move its file here and add a row to the table below.

**Format:** each entry is a copy of `templates/finding.md` with the root cause, impact and remediation written as general text. No `[[TODO: …]]` markers may remain. The marker key is in `templates/README.md`. The notebook's "New file" lists every `.md` file in this folder except this README.

**Competition day:** copy the library file to `findings/F-XXX-<slug>.md`, fill every `[[FIELD]]` with real evidence, delete the `[[NOTE: …]]` markers, and adjust the severity to context.

| ID | Finding | Default severity | ATT&CK | CWE | Status |
|---|---|---|---|---|---|

Default severities are starting points; set the final rating from what you demonstrated. Keep the "Library text is general" note in a copied entry until you've checked every section against the real finding.

Statuses: ◐ finished (every `[[TODO: …]]` written), ☑ also reviewed against a winning report.
