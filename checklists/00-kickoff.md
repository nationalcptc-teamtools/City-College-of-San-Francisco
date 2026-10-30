# Kickoff Checklist (first 30 minutes)

## Quick start (copy-paste, once per person)

Replace `<yourname>` (lowercase, e.g. `alice`) and `<repo-clone>` (where you cloned this repo).

```
<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>
cd ~/cptc-work
nohup python3 -u tools/notebook.py --name <yourname> > ~/notebook.log 2>&1 &
sleep 1; cat ~/notebook.log
scripts/logged-shell.sh <yourname>
```

- Line 1 refuses if `~/cptc-work` already exists. Skip it if you have already made your copy.
- Line 3 starts the notebook in the background. It keeps running if you close the terminal.
- Line 4 prints the address (`Notebook: http://127.0.0.1:8765`). Open it in Firefox.
- Line 5 starts your logged shell.
- Stop the notebook: `pkill -f tools/notebook.py` (stops every notebook you started, including one on another port)
- Port already in use? Add `--port 8766` to line 3.

## Checklist

- [ ] Read the **Scope of Work** and **Rules of Engagement** aloud to the whole team
- [ ] Write the **in-scope ranges** and the **explicit exclusions** on the whiteboard
- [ ] Note any ROE limits on: password spraying, poisoning/relay, DoS-prone tests, social engineering, OT/ride systems, data exfiltration
- [ ] Record the client contacts and how to reach the Operations Team
- [ ] Record the deliverable deadlines and set timers for each one
- [ ] Assign roles (see `WORKFLOWS.md`) and the first-hour targets
- [ ] Check your box against TOOLS.md; tell the team about anything missing.
- [ ] Everyone makes their working copy **first** with `<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>` (README → "Working copy and moving files on the day"; it refuses if `~/cptc-work` already exists, and copies only what is committed in that clone) and works only inside it. It also creates `field-notes/<yourname>/`, `incoming/`, `tracker/`, an empty `exclude.txt` and your saved name. Do this before any logged shell, so logs and scan output never land in the git clone.
- [ ] Agree how finding IDs are allocated and write it on the whiteboard (**TBD**, R6: a shared doc, or per-person blocks such as F-001 to F-020, F-021 to F-040; blocked by the open question "Is shared storage or a shared document provided?")
- [ ] Everyone runs `~/cptc-work/scripts/logged-shell.sh <name>` from inside `~/cptc-work` (or adds the auto-start block to `~/.zshrc`), starts a PowerShell transcript on the Windows box, and checks the system clock. How to use both: `tools/README.md`.
- [ ] Optional: start the notebook from inside `~/cptc-work` with `python3 tools/notebook.py --name <yourname>` and open the address it prints. It shows the checklists and your own files and makes new files from the templates. Local to your box only; how to use it: `tools/README.md`.
- [ ] Confirm with Operations how files may move between our boxes (shared storage, `scp`/`rsync`, or manual export); decide the method and who the report writer pulls from
- [ ] If the report writer pulls over SSH: each teammate changes the default `kali` password, then runs `sudo systemctl start ssh`. Then the report writer runs `scripts/pull.sh --setup` (each teammate's name, login and IP; one password each, once)
- [ ] Build `~/cptc-work/exclude.txt` from the SOW exclusions (scans use `--excludefile exclude.txt`). Whoever identifies an OT host says so aloud and writes it on the whiteboard, and everyone appends it to their own `exclude.txt` tagged `# OT`, for example `10.0.5.20  # OT`. No tool shares this file between machines (**TBD:** blocked by the open question "Is shared storage or a shared document provided?").
- [ ] Check that `~/cptc-work/tracker/` exists (`make-workcopy.sh` copies it from `templates/tracker/`). How the team shares it is **TBD** (blocked by the open question "Is shared storage or a shared document provided?"); see `templates/tracker/README.md`.
- [ ] Agree on the "stop and tell the team" triggers: anything goes down, an account locks, an unexpected host shows up, or a sensitive system responds
- [ ] **If unsure whether a target is in scope, ask Operations before touching it.**

## Midpoint (halfway through the event)
- [ ] The report writer copies `templates/report.md` to `~/cptc-work/report.md` and starts assembling the report there
- [ ] Check `attack-path.csv`: if a path reaches a critical asset, write the chain finding (rule R9)
- [ ] Executive summary draft v0
- [ ] Every finding so far has evidence and an owner
- [ ] Send a client status update (`templates/status-update.md`)

## Final 90 minutes
- [ ] No new exploitation. Writing only.
- [ ] If `tools/compile.py` is built: `python3 tools/compile.py --final` (see `tools/README.md`). The exported PDF/DOCX still needs the manual checks in the QA sheet.
- [ ] Severity consistency pass
- [ ] Remediation steps are specific and testable
- [ ] Spell check, and check that IDs match evidence filenames
- [ ] Run `checklists/50-report-qa.md` on the exported report before submitting
- [ ] Record cleanup status of anything left on systems
