# Workflows

Two roles:

- **Everyone:** tests, takes notes (optionally in `tools/notebook.py`, if built; see `tools/README.md`) and writes up their own findings.
- **The report writer:** from the Report Writing lane (Roster, in Drive); assembles and submits the report.

Every other job (severity review, the findings index, incident reports, status updates, injects, talking to Operations) is shared. `CONVENTIONS.md` §2 says how each rule is enforced.

Commands and file names match `README.md` (working copy) and `templates/README.md` (naming, markers). If they disagree, fix this file.

## 1. Everyone (all day)

1. **Set up (kickoff).** Make your working copy: `<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>` (`README.md` → Working copy). It copies only what's committed, creates your folders and saves your name.
2. **Start every terminal** with `~/cptc-work/scripts/logged-shell.sh`, from inside `~/cptc-work`. It names the logs with your saved name.
   - A name you type after it wins. Lowercase letters, digits and `-`, starting with a letter or digit, or nothing is logged.
   - With neither, it warns and uses your login, which may be `kali` on every box.
   - How it works: `tools/README.md`.
3. **Work from the checklist** for what you're testing (`checklists/10`, `15`, `20`, `30`, `60`). Record hosts and credentials in your tracker rows (`templates/tracker/README.md`).
4. **Log every change you make** on a client system (account created, password changed, file dropped, service touched) in `created-accounts-and-artifacts.csv`, the moment you make it. Appendix F and the cleanup list come from this file.
5. **Tell the team before touching OT.** Before sending any traffic to suspected ride or OT systems (`checklists/30`).
6. **Stop and tell the team** if anything goes down, an account locks, an unexpected host appears or a sensitive system responds (R10).
   - Tell Operations immediately. The written incident report follows within the hour. (**Unconfirmed:** open question "What do the rules require for incident reports, and how fast?")
7. **Found something? Take an ID the moment you find it.** How IDs are allocated is **TBD** (R6; open question "Is shared storage or a shared document provided?").
8. **Create the file:** copy `templates/finding.md` (or a matching `findings-library/` entry) to `~/cptc-work/findings/F-NNN-short-name.md`. `notebook.py` does this if it's built (`tools/README.md`).
9. **Fill it in:**
   - every `[[FIELD]]` and `[[CHOOSE]]`
   - delete every `[[NOTE]]` once you've followed it
   - reproduction steps: an exact command and an `Expected:` line each (R7)
10. **Evidence:** screenshots as `evidence/F-NNN-01.png` (`checklists/40`). Redact secrets to first and last characters.
11. **Hand over** to the report writer (their `scripts/pull.sh`, or a zip; `README.md` → Working copy).
    - Keep editing your own file when they ask for changes. The next pull brings them across.
    - Once a finding is pasted into `report.md`, the report writer makes further changes there (R18). Tell them about yours.
    - If they fix a pasted finding of yours, fix your own file the same way, so the next pull clears it from the QA report.
12. **Clean up** what you created (your `created-accounts-and-artifacts.csv` rows) and mark each row `cleaned_up`, before access ends at **6:00 PM** (reports due 11:59 PM; regional timeline).
    - Pull everything you need off the boxes first (evidence, logs, tracker rows).

## 2. The report writer (from the midpoint)

1. **At the midpoint,** copy the template once: `cp ~/cptc-work/templates/report.md ~/cptc-work/report.md`.
2. **Pull teammates' files** into `incoming/<name>/`, from inside `~/cptc-work`:
   - `scripts/pull.sh` for everyone, `scripts/pull.sh <name>` for one. Set up once at kickoff with `scripts/pull.sh --setup` (`README.md`).
   - It names anyone it couldn't pull. Pull them again later.
   - Or unzip a teammate's export there, fresh each time: delete their `incoming/<name>/` first (`README.md`), so deleted files don't linger.
   - Merge each person's `tracker/` by hand: created-accounts rows for Appendix F, attack-path rows for the Attack Path section.
3. **Run `python3 tools/compile.py`** (if built; what it writes to `build/` and how to read it: `tools/README.md`). Without it, paste findings by hand, ordered by severity.
4. **Paste into `report.md`:**
   - `build/findings-summary.md` → Section 3
   - `build/interactions-timeline.md` → Section 7
   - counts → Executive Summary
   - These are regenerated tables: safe to replace each time.
5. **Paste each finding into Section 5 once,** when it shows READY **and** has no problem lines of its own in `build/qa-report.txt`.
   - READY doesn't cover every check. A READY finding can still fail one (e.g. reproduction steps).
   - Make later changes in `report.md` (R18). Re-pasting would overwrite them.
   - If the author changes a finding after it was pasted, update it by hand in `report.md`.
6. **Fix what the QA report lists.**
   - Not yet pasted: ask the author to fix it.
   - Already pasted: fix it in `report.md` **and** ask the author to fix their own file, so the next pull clears it. Otherwise `compile.py` keeps reporting it, and if it's an error, `--final` fails on every run.
   - Repeat steps 2–5 as new findings arrive.
7. **Final 90 minutes,** in this order:
   1. `python3 tools/compile.py --final` (if built; `tools/README.md`)
   2. export (format and method TBD; open questions "What report format is submitted?" and "Screenshots and export")
   3. the manual pass in `checklists/50-report-qa.md`, with a second person, on the exported file and the Markdown (several items need the exported file)
   4. fix what it finds in `report.md`
   5. export again
   6. submit (method TBD; open question "How is the report submitted?")
8. **After submitting,** nothing from the engagement goes into the repo (R3).
