# Templates: Usage Key

Every template in this repo uses the same placeholder markers. That way one search before submission finds everything that still needs filling in or deleting.

## Placeholder markers

| Marker | Meaning | Example | What to do with it |
|---|---|---|---|
| `[[FIELD_NAME]]` | A value to fill in | `[[CLIENT_NAME]]`, `[[HOST_IP]]` | Replace the whole marker, brackets included, with the real value |
| `[[CHOOSE: A / B / C]]` | Pick one option | `[[CHOOSE: Critical / High / Medium / Low / Informational]]` | Keep only the option you chose |
| `[[NOTE: ...]]` | Guidance for the writer | `[[NOTE: One page, written last.]]` | Read it, follow it, then delete the whole marker |
| `[[TODO: ...]]` | Study-day work in `findings-library/` | `[[TODO: root cause in your own words]]` | Write it during study. None may remain on competition day |

Rules:

- **Why `[[ ]]`:** it doesn't collide with pentest evidence.
  - `{{ }}` collides with template-injection payloads (`{{7*7}}`) and Jinja-based report tools.
  - `<< >>` collides with shell heredocs (`<<EOF`).
  - Bash tests use `[[` too, but always with a space after (`[[ -f x ]]`), so the QA search skips them.
- **Names are UPPER_SNAKE_CASE: capital letters and underscores only, no spaces and no digits** (write `[[SECOND_HOST]]`, not `[[HOST2]]`). That's what keeps the QA search exact: it matches `[[` followed immediately by uppercase letters.
- **If you write in Obsidian,** it will show `[[...]]` as links. That's harmless; the text stays visible.
- **Options are separated with `/`, not `|`.** A `|` inside a Markdown table cell would split the column.
- **One item's details are labelled list lines, not a table:** `- **Severity:** High`.
  - Tables appear only in `report.md` and in what `compile.py` generates. A `|` or line break typed into a value breaks a table.
  - Keep the leading `- `. Without it, Markdown joins the lines into one paragraph.
- **The same name always means the same value.** `[[CLIENT_NAME]]` is the client's name everywhere, so you can find-and-replace it in one go.
  - Two different values of the same kind get their own names: `[[TIME_DETECTED]]`, `[[TIME_REPORTED]]`.
  - A section with a variable number of items, such as reproduction steps, gets one marker for the whole section (`[[REPRODUCTION_STEPS]]`), not one per item.
  - **Exception:** repeating rows and list items in `report.md` (one per finding, per roadmap action, per top risk). You copy those once per item, so their markers repeat on purpose.
- **Checklists use a different style on purpose.** Command arguments in `checklists/` are written `<range>`, `<host>`, `$DC` and so on. Those get typed at the terminal and never reach the report, so they're not markers.
- **A finished deliverable contains zero markers.** `checklists/50-report-qa.md` has the search command.

### Standard field names

Use these names rather than inventing new ones for the same thing.

| Name | Format |
|---|---|
| `[[CLIENT_NAME]]`, `[[CLIENT_CONTACT]]` | As written in the scope document |
| `[[FIRM_NAME]]`, `[[SENDER_NAME]]`, `[[TESTER]]` | Our in-character firm name and people. No school identifiers |
| `[[FINDING_ID]]`, `[[FINDING_TITLE]]` | `F-001`, `F-002`, … (allocation TBD, R6) |
| `[[IR_ID]]`, `[[REFERENCE]]` | `IR-001`, `IR-002`, … (`[[REFERENCE]]` is the IR or inject a `report.md` timeline row points to) |
| `[[DATE]]`, `[[TIME]]`, and suffixed forms like `[[TIME_DETECTED]]` | `YYYY-MM-DD`, `HH:MM` (24-hour, local; the general convention is in `CONVENTIONS.md`, comp repo) |
| `[[ENGAGEMENT_START]]`, `[[ENGAGEMENT_END]]`, `[[REPORT_DATE]]` | `YYYY-MM-DD` |
| `[[HOST]]`, `[[HOST_IP]]`, `[[URL]]`, `[[ACCOUNT]]` | As observed |
| `[[CVSS_VECTOR]]`, `[[CVSS_SCORE]]` | `CVSS:3.1/AV:N/AC:L/...` and `9.8` |

### File names

| File | Name |
|---|---|
| Finding | `findings/F-001-short-name.md` |
| Incident report | `field-notes/<yourname>/IR-001-short-name.md` |
| Other event files (type prefix) | `field-notes/<yourname>/NOTE-short-name.md`, `field-notes/<yourname>/SU-short-name.md` (status update), `field-notes/<yourname>/INJ-short-name.md` (inject response). The prefix says what the file is; it's never a `[[ ]]` tag, which QA would flag. `notebook.py` builds these names from a title and a type dropdown |
| Evidence | `evidence/F-001-01.png`; Burp items `evidence/F-001-01-request.txt` (`checklists/40-evidence-and-logging.md`) |
| Terminal logs | `~/cptc-logs/<name>_<UTC time>.log` and `.cmds.log` (`scripts/logged-shell.md`) |

## Which template, when

| Template | Use it for | Who fills it | When |
|---|---|---|---|
| `finding.md` | One file per finding, copied to `findings/F-XXX-short-name.md` | The finder (R18) | The moment a finding is confirmed |
| `severity-guide.md` | Reference, not a deliverable | Everyone, when assigning severity; ratings are made consistent in one review pass (R8) | When assigning or reviewing severity |
| `report.md` | The final report. Copied once to `~/cptc-work/report.md` (not into `findings/`) | The report writer | Copied at the midpoint, about 2 PM; see `WORKFLOWS.md` |
| `CPTC_2026_Report_Template.docx` | The Word version of the report (same sections as `report.md`). Open it in Word or Google Docs; LibreOffice may refuse it | The report writer | Only if the final report is submitted as a Word file |
| `incident-report.md` | Anything we caused or might have caused | Whole team (R10) | Timing TBD (open question "What do the rules require for incident reports, and how fast?") |
| `status-update.md` | Scheduled or ad-hoc progress messages to the client | Whole team (R13) | Midpoint, and whenever a critical is found |
| `inject-response.md` | A client request during the event | Whole team | Before the inject's due time |
| `presentation-outline.md` | Planning the debrief slides | Whole team | After the report is submitted |
| `tracker/` | Hosts, credentials, created accounts and artifacts, attack path, and findings index (CSV) | Everyone (own rows); `compile.py` checks the findings index (R17) | Copied to `~/cptc-work/tracker/` at kickoff. Sharing method TBD (blocked by the open question "Is shared storage or a shared document provided?"); see `tracker/README.md` |

## The workflow from finding to report

1. Confirm the finding and take an ID straight away (how IDs are allocated is **TBD**, R6; blocked by the open question "Is shared storage or a shared document provided?").
2. Copy `templates/finding.md` (or a matching `findings-library/` entry) to `findings/F-XXX-short-name.md`.
3. Fill every `[[FIELD]]`, resolve every `[[CHOOSE]]`, and delete every `[[NOTE]]` as you go.
4. Hand it to the report writer. You keep editing your own file until it's pasted into `report.md`; after that, changes are made in `report.md` (R18). A finding without complete reproduction steps is sent back (R7); severity is made consistent in one review pass (R8).
5. At the midpoint the report writer copies `templates/report.md` to `~/cptc-work/report.md` and pastes the finished findings into it, ordered by severity (`WORKFLOWS.md`).
6. Before every submission, run `checklists/50-report-qa.md`.
