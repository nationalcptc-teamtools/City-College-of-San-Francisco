# CPTC Team Repo

Pre-staged templates, checklists, and scripts for the Collegiate Penetration Testing Competition (CPTC12, Regionals).

## Rules that govern this repo (from the official rulebook, Oct 2025 revision)

- **This repo is public.** Other teams and the internet can read it. Never put credentials, client data, or anything from the competition environment in here, during or after the event (rule R3).
- **During competition hours,** teams "may make changes to the content on their repository … from the Competition Environment." Our reading: only from there, never from a personal machine.
- **Be ready to explain anything in `scripts/` and `tools/`.** We may be asked to demonstrate or explain it. How each one works: `tools/README.md`.
- **No coach commits.**
- **No outside collaboration tools** (Google Docs, M365, Dropbox) unless officials provide them. The templates here are Markdown so they work in whatever environment we're given.
- **Printed checklists are allowed.**

Source: the [official rulebook](https://cp.tc/docs/cptc-rules.pdf).

## Layout

**Start with `CONVENTIONS.md`, then `WORKFLOWS.md`.** This README is the map and the rulebook summary.

| Path | What it is |
|---|---|
| `CONVENTIONS.md` | **Team rules (R1–R18) and the general naming and format conventions**, each linked to the document with the detail. Start here |
| `WORKFLOWS.md` | Step-by-step walkthroughs for everyone and for the report writer: what to do, in what order, with which file or command |
| `templates/README.md` | The `[[…]]` marker key and which template to use when. Read before filling anything in |
| `templates/finding.md` | One finding (copied once per finding) |
| `templates/report.md` | The full report skeleton (copied once, to `~/cptc-work/report.md`) |
| `templates/severity-guide.md` | How to rate severity (CVSS 3.1 plus context) |
| `templates/incident-report.md`, `status-update.md`, `inject-response.md` | The three client-communication documents |
| `templates/presentation-outline.md` | Plan for the debrief slides after submission |
| `templates/tracker/` | Five CSV files (hosts, credentials, created accounts, attack path, findings index) and their README |
| `findings-library/` | Finished library entries: pre-written findings. Copy one into `findings/` on the day |
| `checklists/` | Printable run sheets: `00` kickoff, `10` AD, `15` Linux, `20` web, `30` OT-safe, `40` evidence and logging, `50` report QA, `60` AI/LLM |
| `scripts/`, `tools/` | The logged shell, `compile.py` and the notebook. How to run each one, and its rules: **`tools/README.md`** |
| `findings/` | One file per finding during the event (`F-001-short-name.md`). Used in the **working copy**, never committed (see below) |
| `evidence/` | Screenshots and logs, named to match the finding ID. Same rule |
| `field-notes/`, `incoming/`, `build/` | Created in the working copy on the day, never committed: your own notes and reports; teammates' pulled files (read-only); `compile.py` output |
| `.gitignore` | Keeps event files (findings, evidence, scan output, credentials) out of git if anyone commits by mistake |

## The workflow on the day

1. Kickoff checklist: read the scope and ROE aloud, then write the out-of-scope list on the whiteboard.
2. Everyone makes their working copy (see "Working copy and moving files on the day" below), then starts a logged shell inside it (`scripts/logged-shell.sh <yourname>`; how: `tools/README.md`).
3. Every finding gets an ID the moment it's found, before it gets exploited further. How IDs are allocated is **TBD** (R6: a shared doc, or per-person blocks such as Alice F-001 to F-020, Bob F-021 to F-040; blocked by the open question "Is shared storage or a shared document provided?").
4. The finder fills in `templates/finding.md` (or a library entry) and hands it to the report writer. The author keeps editing their own file until the finding is pasted into `report.md`; after that, changes are made in `report.md` (R18). Severity is made consistent in one review pass (R8).
5. If something breaks, stop and tell the team. An incident report follows (`templates/incident-report.md`; how fast: **TBD**, open question "What do the rules require for incident reports, and how fast?").
6. Report assembly starts at the halfway point, not at the end. The report writer (see `WORKFLOWS.md`) copies `templates/report.md` to `~/cptc-work/report.md` and works there.
7. Before every submission, someone who didn't write it runs `checklists/50-report-qa.md`.

## Working copy and moving files on the day

**Work in a copy, not in the git clone.** At kickoff, each person runs, from anywhere:

```
<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>
```

Replace `<repo-clone>` with the path of the clone on your box (or give a Git URL as the second part instead) and `<yourname>` with your name in lowercase letters, digits and `-` (e.g. `alice`). The script clones the repo into `~/cptc-work` and deletes the copy's `.git`, so nothing in it can be committed. It then creates `field-notes/<yourname>/`, `incoming/`, `tracker/` (a copy of `templates/tracker/`), an empty `exclude.txt` (the scans' skip list) and `.cptc-name` (your name, which `scripts/logged-shell.sh` uses). It refuses to run if `~/cptc-work` already exists, so it never overwrites event work. It needs `git` and no `sudo`. What it prints when something goes wrong: `tools/README.md`.

**It copies only what is committed in that clone.** It runs `git clone`, so each file arrives at its last committed version: uncommitted edits and deletions, and files git doesn't track, are not carried over. Run `git status` in the clone first and commit or sort out anything it lists.

Practice runs and tool tests should use a different folder (how: `tools/README.md`).

**Do this before starting any logged shell, and open every terminal in `~/cptc-work`.** The checklists write scan output to the current directory; inside the clone, one stray `git add` would publish it.

All event work happens inside `~/cptc-work`: `findings/`, `evidence/`, `field-notes/<yourname>/`, your tracker copy, and later `report.md`. Every path in the templates and checklists stays the same; you're simply working in the copy.

**Picking up a tool fix mid-event:** `make-workcopy.sh` refuses to run again once `~/cptc-work` exists. Copy just the changed file from a fresh clone, for example `cp <repo-clone>/tools/compile.py ~/cptc-work/tools/`.

**Getting files to the report writer.** At kickoff, pick the first of these that works, in order:

1. **Shared storage provided by the officials.** It's explicitly allowed, so use it if it's offered.
2. **Report writer pulls over SSH** with `scripts/pull.sh`, from inside `~/cptc-work`:
   ```
   scripts/pull.sh --setup    # once at kickoff: each teammate's name, login and IP, then one password each
   scripts/pull.sh            # pull every teammate
   scripts/pull.sh alice      # pull one teammate
   ```
   First, each teammate changes the default `kali` password and starts `sshd` (`sudo systemctl start ssh`); their box also needs `rsync`. `--setup` saves the list in `~/cptc-work/teammates.txt`, creates a pull key `~/.ssh/cptc_ed25519` if it isn't there, and runs `ssh-copy-id` once per teammate, so each teammate's password is typed once, at setup. It asks for each teammate's login, so it doesn't assume every box uses `kali`. Each pull copies only `findings/`, `evidence/`, `field-notes/` and `tracker/` from that teammate's `~/cptc-work/` into `~/cptc-work/incoming/<name>/`, over one connection, and writes nothing on the teammate's box. If a teammate can't be reached, the others are still pulled and the script names who failed. If a key copy fails at setup (say, a teammate's SSH server wasn't started yet), fix it and run `scripts/pull.sh --setup` again: answer anything but `yes` to keep the list. Setup re-checks the kept list and runs the key copy again for every listed teammate; `ssh-copy-id` usually skips a teammate who already has the key. The scripts use no `sudo`. Details, and what to do when something fails: `tools/README.md`. The report writer merges teammates' tracker rows (from `incoming/<name>/tracker/`) by hand for the attack path and Appendix F.
3. **Exported bundle, moved by hand.** Each person makes one archive (the notebook's export zip, see `tools/README.md`, or `zip -r` by hand) and drops it on the report writer's machine any way that works (RDP drive mapping, `scp`). Unpack it fresh each time, so files the teammate deleted don't linger: `rm -rf ~/cptc-work/incoming/alice && unzip <file> -d ~/cptc-work/incoming/alice/`.

Whatever the method, incoming work lands in `~/cptc-work/incoming/<name>/` on the report writer's machine. Assembly tooling reads from there, so the method of transfer doesn't matter.

**`incoming/` is a read-only mirror. Nobody edits anything in it.** Every pull overwrites it: `pull.sh` also deletes files the teammate has deleted, and anything in `incoming/<name>/` outside those four folders. Changes to a finding are made by its author in their own `findings/`, and the next pull brings them across; once a finding is in `report.md`, changes are made there (rule R18 in `CONVENTIONS.md`).

**Rules check:** the rulebook bans *external* private storage and "peer to peer or distributed file sharing clients or servers" ("unless specifically authorized by the competition officials"). Copying files between our own team's boxes inside the environment is fine: confirmed Oct 20 that all Kali and Windows boxes share one subnet and `sftp`/`rsync` work. Never move event data anywhere outside the competition environment.
