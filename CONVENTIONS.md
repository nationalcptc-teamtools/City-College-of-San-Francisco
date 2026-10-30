# Team Conventions and Rules

Rules and how we work. Open questions and unconfirmed items are in the team Drive's Open Questions doc; each entry links to the details.

## 1. Competition rules

[Official CPTC Rulebook](https://cp.tc/docs/cptc-rules.pdf) - summary in `README.md` → "Rules that govern this repo".

- The repo is public, and any pre-staged scripts or code must live in it.
- Teams "may be asked to demonstrate or explain their pre-written scripts or code during the event."
- No *external* private storage usage, and no "peer to peer or distributed file sharing clients or servers" on competition networks "unless specifically authorized by the competition officials."
- Incident reports: a detailed (timely) report may reduce the penalty. Incomplete, vague or late ones may cause point loss.
- No coach commits. Printed materials are allowed.

## 2. Team rules

| # | Rule | Why | How it's enforced |
|---|---|---|---|
| R1 | **Push code only.** <br> During the comp we can pull and push, but NEVER push engagement material. Pushes go from a separate clone, never from `~/cptc-work`, and the commit contains code only. | The repo is public and every change is timestamped | `~/cptc-work` has no `.git` (R2), so it can't push |
| R2 | **Work in the working copy** `~/cptc-work`, a plain copy with no `.git`. | Nothing from the engagement can be committed, even by accident | The guarded copy command in `README.md` → Working copy; `checklists/00-kickoff.md` |
| R3 | **Nothing from the engagement ever goes in the repo.** <br> client data, credentials, logs, findings, or environment details. | Public repo; the rulebook bars disclosure until finals conclude | R1 and R2; `README.md` → Rules |
| R4 | **Explain it.** <br> Script and Tool usage must be explainable. The full rule is with the tools. | The rulebook's "explain your code" clause | Function-by-function review before merge; `tools/README.md`; `tools/compile-breakdown.md` |
| R5 | **Every terminal is logged.** <br> `logged-shell.sh` (or the zsh auto-start), plus a PowerShell transcript on Windows. | Evidence, incident reports, answering the client | `scripts/logged-shell.md`; `checklists/00`, `40` |
| R6 | **Every finding gets an ID when found.** <br> At kickoff, hand out 20 IDs per person in order (F-001–F-020, F-021–F-040, and so on) and write the blocks on the whiteboard. Take the next free ID in your block; never reuse an ID. | No collisions | `compile.py` flags duplicate IDs; `templates/README.md` |
| R7 | **The reproduction gate.** <br> A finding without numbered steps, exact commands, and expected results is sent back before it goes in the report. | Top Judge criticism of CPTC10 reports | `checklists/50-report-qa.md` (reproduction line); `compile.py --final` |
| R8 | **Severity.** <br> CVSS 3.1 only; rate what was demonstrated; one-line rationale per finding. | Consistency; CPTC10 rating spreads ran from Medium to Critical for the same issue | `compile.py` requires "Why this severity"; one pass over the findings summary (sorted by severity) against the calibration table in `templates/severity-guide.md` |
| R9 | **Rate each finding on its own.** <br> A combined path gets one extra chain finding; choke points set remediation priority, not severity. | Avoids inflating every link | `checklists/00-kickoff.md` (check `attack-path.csv`); `templates/severity-guide.md` |
| R10 | **Stop and tell the team** <br> Unintentional or destructive results or side effects need to be raised; a service or machine goes down, an account locks, an unexpected host appears, or a sensitive system responds <br> An incident report follows | Penalty reduction requires follow through and potentially speed | `templates/incident-report.md`; `checklists/40-evidence-and-logging.md` (incident line) |
| R11 | **OT safety** <br> OT may or may not be in scope; the SOW decides. Identifying OT is ok if done slowly and carefully, one host at a time, with problematic ports excluded from every broad scan, known OT hosts in `exclude.txt`, tagged `# OT`. Anything that writes, sends a command or could disrupt a process is 🔴 Risky: ask the captain, client, or organizers first, then log the request and response. | Theme-park rides are safety-critical | Scans use `--excludefile exclude.txt`; `checklists/30-ot-ics-safe.md` |
| R12 | **If unsure about scope, ask.** | ROE violations cost points | Scope and exclusions on the whiteboard (`checklists/00-kickoff.md`) |
| R13 | **Notify the client of criticals during the event.** <br> Provide a status update; don't wait them for the report. | Client communication is scored | `templates/status-update.md` |
| R14 | **Report assembly starts around the midpoint.** <br> About halfway through the engagement, the report writer copies `templates/report.md` to `~/cptc-work/report.md` and starts pulling findings in. | The final hours are where CPTC10 reports degraded | `checklists/00-kickoff.md` → Midpoint; `WORKFLOWS.md` §2 |
| R15 | **QA before every submission.** <br> Have someone else double check | Placeholders, broken TOCs and count mismatches were common judge complaints | `checklists/50-report-qa.md` |
| R16 | **Credentials stay in the environment.** Report them redacted to the first and last characters. | Public repo; professionalism | `checklists/40-evidence-and-logging.md`; `templates/tracker/README.md` |
| R17 | **Tracker.** <br> Everyone edits their own rows; the findings index lists every finding ID. | Avoids overwrites | `compile.py` flags IDs missing from or extra to `findings-index.csv`; `templates/tracker/README.md` |
| R18 | **Only edit your own files and findings.** <br> Everyone owns their findings until they're pasted into `report.md`; after that, changes go in `report.md`. Paste each finding once, when `compile.py` shows READY. `incoming/` is a read-only mirror. | Prevents multiple-editor conflicts; no file moves or tool special cases | `compile.py` READY status; `README.md` → Working copy; `WORKFLOWS.md` |

## 3. Naming and format conventions

The apps' and scripts' own formats found in their home:
- `templates/README.md`
- `scripts/logged-shell.md`

The general conventions are below.

| Convention | Format | Documented in |
|---|---|---|
| Checklist command arguments | `<range>`, `<host>`, `$DC`: typed at the terminal, never markers | `templates/README.md` |
| Dates and times | `YYYY-MM-DD`, `HH:MM` (24-hour, local) | `templates/README.md` |
| Severity | Always written as a word (Critical / High / Medium / Low / Informational), never shown by color alone | `templates/severity-guide.md` |
| CVSS | `CVSS:3.1/AV:…` vector plus score | `templates/severity-guide.md` |
| Event folders | `~/cptc-work/` working copy (the report is `~/cptc-work/report.md`); `field-notes/<name>/` for notes; `incoming/<name>/` for teammates' files | `README.md` → Working copy; `tools/BUILD-SPEC.md` |
| Checklist numbering | `00` kickoff, `10` AD, `15` Linux, `20` web, `30` OT, `40` evidence, `50` report QA, `60` AI/LLM | `README.md` → Layout |
| Text format | Markdown, which in practice means plain text. Structure comes from the templates: headings and labelled list lines (`- **Severity:** …`). Tables only in `report.md` and in `compile.py` output | `templates/README.md`; `tools/BUILD-SPEC.md` |
