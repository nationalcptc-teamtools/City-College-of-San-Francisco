# Workflows

Two roles:

- **Everyone:** tests, takes notes (optionally in `tools/notebook.py`, if built; see `tools/README.md`) and writes up their own findings.
- **The report writer:** from the Report Writing lane (Roster, in Drive); assembles and submits the report.

Every other job (severity review, the findings index, incident reports, status updates, injects, talking to Operations) is shared. `CONVENTIONS.md` §2 says how each rule is enforced.

The commands and file names here match `README.md` (working copy) and `templates/README.md` (naming, markers). If they ever disagree, fix this file.

## 1. Everyone (all day)

1. **Set up (kickoff).** Make your working copy with `<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>` (`README.md` → Working copy). It copies only what is committed in that clone, creates your folders and saves your name. Then start every terminal with `~/cptc-work/scripts/logged-shell.sh` from inside `~/cptc-work`: it names the logs with that saved name. A name you type after it wins, and must use lowercase letters, digits and `-`, starting with a letter or digit, or nothing is logged. With neither, it warns and uses your login, which may be `kali` on every box. How the logged shell works: `tools/README.md`.
2. **Work from the checklist** for what you're testing (`checklists/10`, `15`, `20`, `30`, `60`). Record hosts and credentials in your tracker rows (`templates/tracker/README.md`).
3. **Log every change you make** on a client system (an account created, a password changed, a file dropped, a service touched) in `created-accounts-and-artifacts.csv` at the moment you make it. The report's Appendix F and the cleanup list come from this file.
4. **Tell the team before touching OT.** Before sending any traffic to suspected ride or OT systems, say so (`checklists/30`).
5. **Stop and tell the team** if anything goes down, an account locks, an unexpected host appears or a sensitive system responds (R10). Tell Operations immediately; the written incident report follows within the hour (**Unconfirmed:** blocked by the open question "What do the rules require for incident reports, and how fast?").
6. **Found something?** Take an ID the moment you find it. How IDs are allocated is **TBD** (R6; blocked by the open question "Is shared storage or a shared document provided?").
7. **Create the file:** copy `templates/finding.md` (or a matching `findings-library/` entry) to `~/cptc-work/findings/F-NNN-short-name.md`. (`notebook.py` does this if it's built; see `tools/README.md`.)
8. **Fill it in:** every `[[FIELD]]`, every `[[CHOOSE]]`, delete every `[[NOTE]]` once you've followed it. Reproduction steps need an exact command and an `Expected:` line each (R7).
9. **Evidence:** save screenshots as `evidence/F-NNN-01.png` (`checklists/40`). Redact secrets to first and last characters.
10. **Hand over** to the report writer (their `scripts/pull.sh`, or a zip; `README.md` → Working copy). You keep editing your own file when the report writer asks for changes; the next pull brings them across. Once a finding has been pasted into `report.md`, any further change is made there by the report writer (R18), so tell them about it. If the report writer fixes a pasted finding of yours, fix your own file the same way, so the next pull clears it from the QA report.
11. **Clean up** what you created (from your `created-accounts-and-artifacts.csv` rows) and mark each row `cleaned_up`, before access to the environment ends at **6:00 PM** (reports are due at 11:59 PM; regional timeline). Stop testing early enough to pull everything needed off the boxes first (evidence, logs, tracker rows), and clean up before the cutoff.

## 2. The report writer (from the midpoint)

1. **At the midpoint,** copy the template once: `cp ~/cptc-work/templates/report.md ~/cptc-work/report.md`.
2. **Pull teammates' files** into `incoming/<name>/`: run `scripts/pull.sh` from inside `~/cptc-work` for everyone, or `scripts/pull.sh <name>` for one (set up once at kickoff with `scripts/pull.sh --setup`; `README.md`). It names anyone it couldn't pull, so pull them again later. Or unzip a teammate's export there, fresh each time (delete their `incoming/<name>/` first, as `README.md` says), so files they deleted don't linger. That includes each person's `tracker/`: merge their created-accounts and attack-path rows by hand for Appendix F and the Attack Path section.
3. **Run `python3 tools/compile.py`** (if built; what it writes to `build/` and how to read it: `tools/README.md`). Without the tool: paste findings by hand, ordered by severity.
4. **Paste into `report.md`:** summary table (`build/findings-summary.md`) into Section 3, timeline (`build/interactions-timeline.md`) into Section 7, counts into the Executive Summary (these are regenerated tables, safe to replace each time). Paste each **finding** into Section 5 **once**, when it shows READY **and** has no problem lines of its own in `build/qa-report.txt` (READY doesn't cover every check: a READY finding can still fail a check, e.g. the reproduction steps), and make any later changes in `report.md` (R18): re-pasting a finding would overwrite those edits. If the author changes a finding after it was pasted, update that finding by hand in `report.md`.
5. **Fix what the QA report lists:** ask the author to fix findings not yet pasted. Fix a pasted one in `report.md` **and** ask its author to fix their own file too, so the next pull clears it; otherwise the problem stays in their file and `compile.py` keeps reporting it; if it is an error, `--final` fails on every run. Repeat steps 2–4 as new findings arrive.
6. **Final 90 minutes,** in this order: run `python3 tools/compile.py --final` (if built; see `tools/README.md`); export (format and method TBD; open questions "What report format is submitted?" and "Screenshots and export"); do the manual pass in `checklists/50-report-qa.md` (with a second person) on the exported file and on the Markdown, because several of its items need the exported file; fix what it finds in `report.md`; export again; submit (method TBD; open question "How is the report submitted?").
7. **After submitting,** nothing from the engagement goes into the repo (R3).
