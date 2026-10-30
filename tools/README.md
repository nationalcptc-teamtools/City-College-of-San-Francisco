# Tools and scripts: how to run them

This is the one README for the team's tools and scripts: `tools/compile.py`, `tools/notebook.py` (built in part), `scripts/make-workcopy.sh`, `scripts/pull.sh` and `scripts/logged-shell.sh`. It says what each one does, how to run it, and the rules every one of them follows.

**Before running anything, make your working copy, `~/cptc-work`,** with `scripts/make-workcopy.sh` (below; also comp repo `README.md` → "Working copy and moving files on the day"). Every other command below runs from inside `~/cptc-work`, never from the git clone.

## Rules for everything in `tools/` and `scripts/`

- **Explain it or it doesn't go in (rule R4).** Every script or tool must be explainable line by line, written by us, standard library only, with no copied code we don't understand. The rulebook says teams "may be asked to demonstrate or explain their pre-written scripts or code during the event." (**Unconfirmed** whether AI-assisted code counts; blocked by the open question "Does the 'explain your code' rule cover AI-assisted code?")
- **Short enough to explain.** Keep every script short enough that any team member can walk through it.
- **No exploit code copied from elsewhere** without understanding it, and **no credentials or targets hard-coded**.
- **Python 3 standard library only** for the tools: no `pip install`.

## What's here

| Path | What it is | Status |
|---|---|---|
| `scripts/make-workcopy.sh` | Makes your working copy `~/cptc-work` from the clone, once at kickoff. Needs `git` | Built |
| `scripts/pull.sh` | The report writer's pull of every teammate's work into `incoming/<name>/`. Needs `ssh`, `ssh-keygen`, `ssh-copy-id` and `rsync` | Built |
| `scripts/logged-shell.sh` | Records every terminal session, with a one-line-per-command index. Needs util-linux `script` (default on Kali/Debian) | Built. Walkthrough: `scripts/logged-shell.md` |
| `tools/compile.py` | Assembles everyone's findings into report-ready Markdown and checks them for QA problems | Built (accepted at milestone M2, 2026-10-21) |
| `tools/notebook.py` | A local web page for the checklists, your own files, new files from the templates, filling them in, the logs and a zip export; later a compile button and a combined Markdown export | Built in part: everything except the compile button and the combined Markdown export |
| `tools/tests/` | Unit tests: `python3 -m unittest discover tools/tests` | Built |

Design docs and function-by-function walkthroughs are in the public app repo, https://github.com/phil-j-fry/cptc-2026-personal (`tools/`).

## Making your working copy: `scripts/make-workcopy.sh`

Once per person at kickoff, before any logged shell. Run it from anywhere:

```
<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>
```

`<repo-clone>` is the clone on your box. A Git URL works as the second part too, if the box can reach it. `<yourname>` uses lowercase letters, digits and `-`, starting with a letter or digit (e.g. `alice`).

**It copies only what is committed in that clone.** It runs `git clone`, so each file arrives at its last committed version: uncommitted edits and deletions, and files git doesn't track, are not carried over. Run `git status` in the clone first and commit or sort out anything it lists.

What it does, in order:

1. Refuses, changing nothing, if `~/cptc-work` already exists (a folder, a file or a symlink), if the name breaks the rule above, or if it doesn't get exactly two arguments.
2. `git clone` of the source into `~/cptc-work`, then deletes `~/cptc-work/.git`, so nothing in the copy can be committed. The clone you copied from keeps its own `.git`.
3. Creates `field-notes/<yourname>/`, `incoming/`, `tracker/` (a copy of `templates/tracker/`), an empty `exclude.txt` (the scans' skip list: SOW exclusions, OT hosts tagged `# OT`) and `.cptc-name` (your name on one line, which `logged-shell.sh` uses).

It needs `git`, uses no `sudo` and doesn't touch anything outside `~/cptc-work`.

**When it fails:**

| It prints | What to do |
|---|---|
| `~/cptc-work already exists, so nothing was changed.` | You already have a working copy. For a tool fix, copy the one file (below). |
| `git clone of <source> failed.` | Check the path or URL. Git usually removes what it started, but a clone that failed partway can leave a partial `~/cptc-work`: if it exists, `rm -rf ~/cptc-work` (nothing of yours is in it yet), then run the script again. |
| `... ~/cptc-work is incomplete: delete it, then run this again.` | The clone worked but a later step didn't (e.g. the source has no `templates/tracker/`, or brings its own `tracker/`, `exclude.txt` or `.cptc-name`, or a symlink where the script writes). This happens in the same run, before any event work, so `rm -rf ~/cptc-work` and run it again (from the right source if that was the problem). The script never deletes it itself. |

## Pulling teammates' work: `scripts/pull.sh`

For the report writer, when the team moves files over SSH (option 2 in the comp repo `README.md` → "Getting files to the report writer"). Run it from inside `~/cptc-work`:

```
scripts/pull.sh --setup    # once at kickoff
scripts/pull.sh            # pull every teammate
scripts/pull.sh alice      # pull one teammate (the exact name from setup)
```

**Before setup,** each teammate changes the default `kali` password and starts their SSH server (`sudo systemctl start ssh`). Their box also needs `rsync`. The report writer's box needs `ssh`, `ssh-keygen`, `ssh-copy-id` and `rsync`. The script itself uses no `sudo`.

**`--setup`** asks how many teammates, then each one's name, login and IP, once each. A name follows the same rule as `make-workcopy.sh`; a login is a lowercase Linux login (e.g. `kali`); an IP is four numbers separated by dots (e.g. `10.0.0.5`; whether each number is 255 or less isn't checked here, so a wrong address shows up when `ssh-copy-id` can't connect). An answer that breaks one of these formats stops setup and saves nothing, so start again. When every answer is fine, it:

- saves the list to `~/cptc-work/teammates.txt` (one `name<TAB>login<TAB>IP` line per teammate, mode 600, owner-only permissions; it holds engagement IPs, and the repo's `.gitignore` lists it),
- creates the pull key `~/.ssh/cptc_ed25519` (no passphrase) if it isn't there yet, or reuses it,
- runs `ssh-copy-id` once per teammate, so each teammate's password is typed once, here. After that, pulls log in with the key.

If the list already exists, `--setup` shows it first. Type `yes` to replace it: setup then asks for every teammate again. Anything else keeps the list: setup checks every line of it the way a pull does (a bad line is named by number, and nothing runs), then does the key step and one `ssh-copy-id` per teammate again, without retyping anyone. `ssh-copy-id` first checks whether a teammate already has the key and skips them if so, so normally only the teammates that failed are asked for a password.

**Each pull** uses one `rsync` connection per teammate. It copies only `findings/`, `evidence/`, `field-notes/` and `tracker/` from the teammate's `~/cptc-work/` into `~/cptc-work/incoming/<name>/`. It deletes files there that the teammate has deleted, and anything in `incoming/<name>/` outside those four folders, so the folder matches what the teammate has now. It never writes on the teammate's box. Nobody edits anything in `incoming/` (rule R18).

**When it fails:**

| It prints | What to do |
|---|---|
| `no teammate list at ... Run setup first` | Run `scripts/pull.sh --setup`. |
| `the key is not on: <names>` (setup) | Those teammates' SSH server isn't running, or the password was wrong. The others are done. Fix it and run `--setup` again, answering anything but `yes` to keep the list. |
| `<name> failed.` and `not pulled: <names>` | That teammate's box is off, unreachable, or doesn't have the key. The others were still pulled; the script exits with an error so a partial pull is never silent. Pull them again later with `scripts/pull.sh <name>`. |
| `no teammate named "<name>"` | Use the exact name from setup (`cat ~/cptc-work/teammates.txt`). |
| `<path> is a symlink` | `incoming/` or `incoming/<name>/` is a link, so nothing is copied through it. Replace it with a plain folder. |
| `... teammates.txt line N: ...` | The list was edited by hand and line N breaks a rule (or repeats a name). Fix that line, or run `--setup` again. |

**After the event:** delete the pull key (`rm ~/.ssh/cptc_ed25519 ~/.ssh/cptc_ed25519.pub`) and `~/cptc-work/teammates.txt`. `ssh-copy-id` added the key's public line to each teammate's `~/.ssh/authorized_keys`; each teammate removes the line that matches `~/.ssh/cptc_ed25519.pub` (copy that file's text to them before deleting it). If setup created the key, that line ends in `cptc-pull`; a key that already existed keeps its own comment.

## Logging every terminal: `scripts/logged-shell.sh`

Start it in every terminal, from inside `~/cptc-work`:

```
scripts/logged-shell.sh [yourname]
```

- **The name on the logs:** the name you give, which must use lowercase letters, digits and `-`, starting with a letter or digit (any other is refused and nothing is logged); without one, the name `make-workcopy.sh` saved in `~/cptc-work/.cptc-name`. If neither is there (or that file doesn't hold one valid name), it uses your login and prints a one-line warning, and logging still starts. Every competition Kali box may log in as `kali` (**Unconfirmed**; open question "Did every box log in as the same user?"), so logs named after the login can't be told apart: give your name, or make the working copy with the script.
- **What it writes:** two files per session in `~/cptc-logs/`: `<name>_<UTC time>.log` (the full transcript) and `<name>_<UTC time>.cmds.log` (one line per command: time, exit code, directory, command). Type `exit` to stop; the file paths are printed.
- **Every new terminal, automatically:** add the zsh auto-start block to `~/.zshrc` (`scripts/logged-shell.md` → "Optional: start logging automatically in every terminal"). It hasn't been tested in zsh yet; try it on your own Kali VM first.
- **Windows box:** the script is Linux-only. Start a PowerShell transcript in every PowerShell window instead (`scripts/logged-shell.md` → "On the Windows box").
- **Finding the lines for a finding:** look up the time in `*.cmds.log`, then open the full transcript with `less -R ~/cptc-logs/<file>.log` (`/` and a word to search, `q` to quit), or in the notebook's Logs view.

Full walkthrough, line by line: `scripts/logged-shell.md`.

## Assembling the report: `tools/compile.py`

### Why it exists

Everyone writes findings, incident reports, status updates and inject responses as Markdown files from the templates. The report writer has to turn them into one report. `compile.py` does the repetitive part, at any point in the event:

- **Report-ready Markdown.** It builds the findings table and severity counts (report Section 3 and the Executive Summary), all findings in severity order (Section 5), and the interactions timeline (Section 7) from the `IR-`, `SU-` and `INJ-` files.
- **QA status.** It runs some of the checks from the report QA list (`checklists/50-report-qa.md`) on the Markdown files, and marks each finding READY or DRAFT, so the report writer can see what is still unfinished and where: file and line, or just the file when there is no line to point at (e.g. a missing labelled line, which the message names).
- **Two modes.** Draft mode (the default) only warns, because unfinished drafts are normal during the event. `--final` is the check before submitting: almost every QA problem becomes an error, and any error makes the run fail (exit code 1).

It only works on the team's own files. It doesn't scan, attack or touch any target.

### What it does NOT do

- **It never edits `report.md`.** Draft mode doesn't open it. `--final` only reads it, to look for leftover markers and older-style leftovers such as `TODO`; fixes in the report are made by hand.
- **It never changes the files it reads.** Findings, timeline files, the findings index and everything in `incoming/` are only read. The only things it writes are the four files in `build/` (it creates `build/` if needed).
- **It never runs commands.** If `pandoc` is installed, it prints the command to convert `report.md`, and you run it yourself.
- **It never uses the network.** It only reads and writes files on your own box.
- **It doesn't fix anything.** It reports problems; people fix the files by hand.
- **It doesn't check the exported PDF or DOCX.** Only the Markdown is checked, so the manual checks in `checklists/50-report-qa.md` (such as the Ctrl-F search of the exported file for `[[`, `XX` and `TODO`) still apply.

### Before you run it

- **Python 3.9 or newer, standard library only.** Nothing to install. Kali normally ships with Python 3, but check `python3 --version` on the event box (what's installed there is still **Unconfirmed**). The tests pass on Python 3.9 and 3.13.
- **A working copy.** It works on `~/cptc-work` by default (`--root PATH` for another folder, e.g. a practice copy). It refuses a folder with `.git` directly inside it (a folder or a file), such as the git clone, before writing anything, so event data doesn't end up in the repo by mistake. It only looks in that one folder: a subfolder of the clone isn't caught.
- **Files named and filled from the templates.** It reads `findings/F-*.md` and teammates' `incoming/*/findings/F-*.md`, the `IR-`, `SU-` and `INJ-` files in `field-notes/*/` and `incoming/*/field-notes/*/`, and `tracker/findings-index.csv` (or `--index PATH`). It reads them by the templates' headings and labelled lines (e.g. `- **Severity:**`), so keep those as the templates have them (file names: `templates/README.md` → File names).
- **Everything stays inside the working copy.** A path that leads outside it, through `..` or a symlink, is refused and named in the error. `build/` and its four output files must be plain folders and files, not links.
- **No notebook needed.** It works on hand-edited files on its own. The notebook's Compile button, when it is built, is planned to call the same code.

### How to run it

```
python3 tools/compile.py [--root PATH] [--index PATH] [--final]
```

| Option | What it does |
|---|---|
| `--root PATH` | The working copy to compile. Default: `~/cptc-work` (never the current folder) |
| `--index PATH` | The findings index. Default: `<root>/tracker/findings-index.csv`. A relative path is taken from the root, and the file must be inside the root |
| `--final` | The strict check before submitting (below) |

The report writer runs it from inside `~/cptc-work`:

```
python3 tools/compile.py            # draft mode: any time during the event
python3 tools/compile.py --final    # final 90 minutes, before every submission
```

**Draft mode** (the default) reports every problem as a `WARNING`, writes all four files and exits 0 (unless it can't run at all: exit code 2, below), because drafts with `[[…]]` markers are normal during the event.

**`--final`** reports almost every problem as an `ERROR` and exits 1 if there is at least one. Two kinds stay warnings, because they can be legitimate: older-style leftovers (e.g. `TODO` in pasted output) and a findings index that is absent, empty or has only its header row (the ID comparison is then skipped).

### What it writes

Four files in `build/` (it creates `build/` if needed). Every run rewrites all four from scratch; other files in `build/` are left alone. It refuses to run if `build/` or one of the four files is a link (a symlink, or a file with a second hard link), and it checks all four before writing any.

| File | What's in it | Goes into the report |
|---|---|---|
| `build/findings-summary.md` | The findings table (ID, Title, Severity, Affected assets, Status), sorted Critical → Informational, findings with no severity word last, then by ID; and the severity count table with a Total | Section 3 and the Executive Summary counts |
| `build/findings-combined.md` | Every finding's full text, in the same order. Each DRAFT is preceded by a banner line such as `[[NOTE: DRAFT: 2 unresolved markers, 1 missing fields]]`, which is itself a marker, so a banner pasted into `report.md` is caught by `--final` | Section 5 |
| `build/interactions-timeline.md` | One row per `IR-`, `SU-` and `INJ-` file (Time, Type, Summary, Reference), sorted by time; a file whose time isn't `YYYY-MM-DD HH:MM` goes last | Section 7 |
| `build/qa-report.txt` | Each finding's READY or DRAFT line, then every check as `PASS` or `FAIL (E errors, W warnings)` with its problems; in `--final`, a separate `report.md:` part | Nothing: it's for the team |

Values go into the tables exactly as written; the tool never edits a finding to make it fit.

### What it prints, and the exit code

The screen shows, in this order:

1. four `WROTE <full path>` lines, one per output file
2. one line per problem: `WARNING: file:line: message` or `ERROR: file:line: message` (just `file:` when there is no line, e.g. a missing labelled line)
3. `--final` only: `report.md checked: N problems` or `report.md NOT FOUND: report not checked`
4. `QA: N findings; R READY; D DRAFT; W warnings; E errors`
5. if `pandoc` is installed, a hint with the command to turn `report.md` into a DOCX (or PDF). The tool never runs it

| Exit code | Meaning |
|---|---|
| 0 | It ran. Always in draft mode; in `--final`, no errors (warnings are fine) |
| 1 | `--final` found at least one error |
| 2 | It couldn't run, in either mode: one `compile failed: <reason>` line instead (e.g. the root has `.git`, a path leads outside the root, a file can't be read or written) |

A check can show `FAIL (0 errors, 1 warnings)` while `--final` still exits 0: only errors change the exit code.

The same work is available from Python without printing: `run(root, index, final)` in `compile.py` returns the exit code, the text of `qa-report.txt` and the screen lines. The tests use it, and the notebook's Compile button is planned to.

### The checks

READY means: no leftover markers, a value in each of the six required fields (Severity, CVSS 3.1, Why this severity, Affected assets, Status, References), a severity word (`Critical`, `High`, `Medium`, `Low` or `Informational`, spelled exactly) and a title. Anything else is DRAFT. READY covers only leftover markers, the six required fields, the severity word and the title. Every other check is reported separately as its own problem lines. Paste a finding into `report.md` only when it is READY **and** has no problem lines of its own: a READY finding can still fail a check, e.g. the reproduction steps.

| Check | What it reports |
|---|---|
| finding headings | No `### F-NNN: Title` heading, a title at the wrong level (e.g. `##`), no title text, no ID, or a heading ID that differs from the filename's |
| labelled lines | A missing labelled line such as `- **Severity:**`, or the same label twice |
| severity | No severity word (the finding sorts last) |
| required fields | One of the six required fields with nothing filled in |
| leftover markers | `[[` followed by capital letters, e.g. `[[HOST]]` or an unclosed `[[HOST` |
| older-style leftovers | `<<`, `TODO`, `F-XXX`, `IR-XXX`, `XX` (as a whole word), `YYYY` or `HH:MM`, outside code blocks and backtick spans. Always a warning |
| reproduction steps | No `#### Reproduction steps` section, no numbered step (digits, a dot, then a space or tab, e.g. `1. `), or fewer `Expected:` lines than steps |
| references | No `http` link on the `References:` line |
| CVSS version | A vector that isn't a full CVSS 3.1 vector, with all eight metrics in the standard order |
| duplicate finding IDs | The same ID in two files, in `findings/` or any `incoming/*/findings/` |
| findings index | An ID missing from the index, an index ID with no finding file, or an index that can't be used |
| summary table | A pipe character in a Title, Affected assets or Status value, which would break the table. A pipe written as backslash-pipe isn't reported. **Limit:** a pipe after two backslashes isn't reported either, though Markdown reads it as a real separator |
| interactions timeline | A missing or badly formatted time, no `#` heading, or a pipe character in that heading (same backslash rule and Limit as the summary table). Also an `IR-`, `SU-` or `INJ-` file at the root's top level or the top of `field-notes/` (or those two spots inside `incoming/<owner>/`): it isn't in `field-notes/<name>/`, so it is left out of the timeline |

### `report.md` and its limits

Draft mode never opens `report.md`. `--final` reads it, if it's in the root, for two checks only: leftover markers (errors) and older-style leftovers (warnings). Its problems are printed on screen and counted like the others, and listed under their own `report.md:` part of `qa-report.txt`. If it's missing, the run says `report.md NOT FOUND: report not checked`; that isn't an error, since the report may be finished in another tool.

**Limits:** it doesn't run the finding checks on `report.md` (a finding pasted there is checked only for markers and older-style leftovers), and it can't read the exported PDF or DOCX. The manual checks in `checklists/50-report-qa.md` still apply.

### One ID = one file

Each finding ID lives in exactly one file, owned by the person who wrote it. If a teammate's finding needs a fix, the owner fixes their own file and sends it again (the next pull or export). That holds after pasting too: a fix made in `report.md` (R18) must also be made in the author's own file, or the problem stays in their file and `compile.py` keeps reporting it; if it is an error, `--final` exits 1 on every run. The report writer doesn't keep a fixed copy in their own `findings/`: a copy there next to the original in `incoming/<name>/findings/` has the same ID, so the duplicate-ID check reports both files, an error in `--final`.

### Example: a practice run

This makes a throwaway practice copy, adds two clearly fake findings and a status update, and runs both modes. Run it on your own Kali VM, never in `~/cptc-work`.

**1. Make the practice copy and add fake files.** Paste this whole block from inside your git clone. It copies the clone like the working-copy command at kickoff, but to `~/cptc-practice`. F-001 is finished; F-002 still has its CVSS markers and a `TODO`. If `~/cptc-practice` already exists (even as a broken symlink), it stops and changes nothing. It writes the fake files only after the copy, the `cd` and the `mkdir` all worked; if any of them fails, it prints `setup failed` and writes no fake files.

```
if [ -e ~/cptc-practice ] || [ -L ~/cptc-practice ]; then
  echo "~/cptc-practice already exists: stop"
elif cp -r "$PWD" ~/cptc-practice && rm -rf ~/cptc-practice/.git && cd ~/cptc-practice && mkdir -p findings tracker field-notes/alice incoming; then
cat > findings/F-001-default-admin-password.md <<'EOF'
### F-001: Default admin password on web01

- **Severity:** Critical
- **CVSS 3.1:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (9.8)
- **Why this severity:** Anyone on the guest network can log in as admin with the vendor default password.
- **Affected assets:** web01 (10.0.0.1)
- **Status:** Exploited
- **References:** CWE-1392, https://example.invalid/default-credentials

#### Reproduction steps
1. `curl -i -d 'user=admin&pass=admin' http://10.0.0.1/login`
   Expected: HTTP/1.1 302 Found, redirecting to /admin
EOF
cat > findings/F-002-smb-signing.md <<'EOF'
### F-002: SMB signing not required on file01

- **Severity:** Medium
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** An attacker on the network can relay logins to file01. TODO check the other file servers.
- **Affected assets:** file01 (10.0.0.2)
- **Status:** Open
- **References:** https://example.invalid/smb-signing

#### Reproduction steps
1. `nxc smb 10.0.0.2`
   Expected: the output shows signing:False
EOF
cat > field-notes/alice/SU-midday.md <<'EOF'
# Status update: midday

- **Time:** 2026-11-07 12:00
EOF
cp templates/tracker/findings-index.csv tracker/
echo 'F-001,Default admin password on web01,Critical,9.8,alice,Exploited,no' >> tracker/findings-index.csv
echo 'F-002,SMB signing not required on file01,Medium,,alice,Open,no' >> tracker/findings-index.csv
echo "practice copy ready: $PWD"
else
  echo "setup failed: remove ~/cptc-practice before trying again"
fi
```

**2. Draft run.** Expected output on a box without `pandoc` (with `pandoc` installed, a `HINT:` line follows the `QA:` line). The `WROTE` paths here are for Kali's default `kali` account; yours show your own home folder:

```
$ python3 tools/compile.py --root ~/cptc-practice
WROTE /home/kali/cptc-practice/build/findings-summary.md
WROTE /home/kali/cptc-practice/build/interactions-timeline.md
WROTE /home/kali/cptc-practice/build/findings-combined.md
WROTE /home/kali/cptc-practice/build/qa-report.txt
WARNING: findings/F-002-smb-signing.md:4: CVSS 3.1 has no value
WARNING: findings/F-002-smb-signing.md:4: leftover marker [[CVSS_VECTOR
WARNING: findings/F-002-smb-signing.md:4: leftover marker [[CVSS_SCORE
WARNING: findings/F-002-smb-signing.md:5: older-style leftover TODO
QA: 2 findings; 1 READY; 1 DRAFT; 4 warnings; 0 errors
$ echo $?
0
```

**3. Final run.** The same problems become errors, except the `TODO`; there is no `report.md` yet (same `pandoc` and path notes as step 2):

```
$ python3 tools/compile.py --root ~/cptc-practice --final
WROTE /home/kali/cptc-practice/build/findings-summary.md
WROTE /home/kali/cptc-practice/build/interactions-timeline.md
WROTE /home/kali/cptc-practice/build/findings-combined.md
WROTE /home/kali/cptc-practice/build/qa-report.txt
ERROR: findings/F-002-smb-signing.md:4: CVSS 3.1 has no value
ERROR: findings/F-002-smb-signing.md:4: leftover marker [[CVSS_VECTOR
ERROR: findings/F-002-smb-signing.md:4: leftover marker [[CVSS_SCORE
WARNING: findings/F-002-smb-signing.md:5: older-style leftover TODO
report.md NOT FOUND: report not checked
QA: 2 findings; 1 READY; 1 DRAFT; 1 warnings; 3 errors
$ echo $?
1
```

**4. The QA report** from that run, `cat build/qa-report.txt`:

```
QA report (--final): any ERROR below fails the run

Findings:
  findings/F-001-default-admin-password.md: READY
  findings/F-002-smb-signing.md: DRAFT: 2 unresolved markers, 1 missing fields

Checks:
PASS finding headings
PASS labelled lines
PASS severity
FAIL (1 errors, 0 warnings) required fields
  ERROR: findings/F-002-smb-signing.md:4: CVSS 3.1 has no value
FAIL (2 errors, 0 warnings) leftover markers
  ERROR: findings/F-002-smb-signing.md:4: leftover marker [[CVSS_VECTOR
  ERROR: findings/F-002-smb-signing.md:4: leftover marker [[CVSS_SCORE
FAIL (0 errors, 1 warnings) older-style leftovers
  WARNING: findings/F-002-smb-signing.md:5: older-style leftover TODO
PASS reproduction steps
PASS references
PASS CVSS version
PASS duplicate finding IDs
PASS findings index
PASS summary table
PASS interactions timeline

report.md:
report.md NOT FOUND: report not checked
```

**5. Clean up** when you're done: `cd ~ && rm -rf ~/cptc-practice`.

## Checklists and your files in your browser: `tools/notebook.py` (built in part)

A page on your own box for the checklists, your own files, new files, filling them in, the logs and a zip export; a compile button and a combined Markdown export are still to come. Start it from inside `~/cptc-work`:

```
python3 tools/notebook.py --name <yourname> [--root ~/cptc-work] [--port 8765]
```

Then open the address it prints (`Notebook: http://127.0.0.1:8765` by default). Ctrl+C stops it.

- **Local only:** it listens on `127.0.0.1`, so only your own box can open it, and there is no option to change that. It's not a server for the team.
- **`--name`:** your name as in `field-notes/<yourname>/` (`Alice Smith` becomes `alice-smith`).
- **`--root`:** the working copy, `~/cptc-work` by default (never the folder you're in). Like `compile.py`, it refuses a folder with `.git` directly inside it, such as the git clone, and prints `notebook failed: ...`.
- **`--port`:** 8765 by default. If that port is taken (e.g. by a second notebook), it prints `notebook failed: can't listen on 127.0.0.1:8765: ...`; choose another with `--port`.

**What it does today:**

- **Checklists:** lists the `.md` files in `checklists/` and shows each task line (`- [ ] ...`) as a checkbox; every other line is shown as it is in the file. Ticks are saved to `field-notes/<yourname>/checklist-state.json`; the checklist files are only read, never changed. Reworded tasks start unticked, since a tick belongs to the task's exact words.
- **Your own files:** the left column lists the `.md` files in `findings/` and `field-notes/<yourname>/`, sorted by name so each kind groups by prefix (`F-`, `INJ-`, `IR-`, `NOTE-`, `SU-`). Teammates' copies in `incoming/` are never listed. A folder or file whose link points outside the working copy isn't listed; the column shows `Not listed:` and the reason instead.
- **New file:** pick a type (Note, Incident report, Status update, Inject response or Finding) and type a title; there is no file name to type. The notebook builds the name and folder (`templates/README.md` → File names): a Finding goes in `findings/`, the others in `field-notes/<yourname>/`, and each starts from its template in `templates/` (a Note starts blank). An incident report and a finding also need a three-digit number. For an incident report the form suggests the next free one (the highest IR number in use plus one). A number already in use (`IR-NNN` or `F-NNN`) gives a warning, but the file is still made. A Finding can start from a `findings-library/` entry instead of the template; picking one puts its title in the Title box. The title must be one line. An existing file is never overwritten: if the name is taken, it says `already exists, choose a different title: <path>`. The new file then shows, selected, in the left column.
- **Fill-in:** clicking one of your files opens it with a box for each `[[MARKER]]` still in it and the whole file below. Save puts the box values into the file; the text below saves itself 2 seconds after you stop typing.
- **Logs:** lists the files in `~/cptc-logs/` (or `$LOGDIR`), newest first, and shows one read-only: cleaned or raw, with a search box, its exact commands from the `.cmds.log`, the `less -R` command to open it in a terminal, and a button that copies it unchanged into `evidence/` under a name you type.
- **Export:** one zip, `cptc-export-<name>-<timestamp>.zip`, saved in the working copy and laid out so unzipping it inside the report writer's `incoming/<name>/` gives the same mirror an `rsync` pull would (option 3 in the comp repo `README.md` → "Getting files to the report writer"). Logs go in only if "Include logs" is ticked (off by default).
- **Light / dark:** follows your system's setting; the button swaps it. Plain black and white with one grey; messages and warnings sit in a bordered block.

**Still to come:** a compile button and a combined Markdown export.

**Until then:** run `compile.py` from the terminal.

## Picking up a tool fix mid-event

`make-workcopy.sh` refuses to run again once `~/cptc-work` exists. Copy just the changed file from a fresh clone: comp repo `README.md` → "Working copy and moving files on the day".

## Walkthrough, manual checks and Operations questions

Each tool's part is added once that tool is finished and reviewed.

### How each tool works, section by section

`compile.py`: "Assembling the report" above goes through it part by part: what it reads, what it writes, what it prints and each check.

### Manual test checklist

Checks a teammate runs by hand on their own Kali VM, never in `~/cptc-work`: after a tool change and before the repo lock. Each one says what to do and what you should see. The `/home/kali/` paths are for Kali's default account; yours show your own home folder.

#### `compile.py`

**Setup:** steps 1–3 of "Example: a practice run" above. Its steps 2 and 3 are the first two checks: the draft run has 4 warnings and exits 0, and `--final` has 3 errors and 1 warning and exits 1. Then work through the list below in order, from inside `~/cptc-practice` (item 9 runs from your git clone). After each run, `echo $?` shows the exit code. Item 4 fills in F-002's CVSS line, and the items after it expect that; any item that adds a file removes it again at its end. When you're done, clean up with step 5 of the example.

1. **Options.** `python3 tools/compile.py --help`
   You should see: the three options `--root`, `--index` and `--final`, and the default root `~/cptc-work`.
2. **The default root is `~/cptc-work`, not the folder you're in.** `HOME="$PWD/manual-test-home" python3 tools/compile.py`
   This points `~` at a folder that doesn't exist for this one run, so the run can't touch a real `~/cptc-work`. You should see: `compile failed: root folder not found: /home/kali/cptc-practice/manual-test-home/cptc-work`, exit 2.
3. **The four outputs.** `ls build`, then open each file.
   You should see: `findings-combined.md`, `findings-summary.md`, `interactions-timeline.md` and `qa-report.txt`.
   - `findings-summary.md` lists F-001 (Critical) above F-002 (Medium), and its count row is `| 1 | 0 | 1 | 0 | 0 | 2 |`.
   - `interactions-timeline.md` has one row: `| 2026-11-07 12:00 | Status update | Status update: midday | SU-midday |`.
   - `findings-combined.md` has `[[NOTE: DRAFT: 2 unresolved markers, 1 missing fields]]` just above F-002's heading, and no banner above F-001.
   - `qa-report.txt` matches step 4 of the example.
4. **`--final` passes with only warnings left.** In `findings/F-002-smb-signing.md`, replace line 4 with ``- **CVSS 3.1:** `CVSS:3.1/AV:A/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N` (5.4)`` and leave the `TODO`. Run `python3 tools/compile.py --root ~/cptc-practice --final`.
   You should see: `WARNING: findings/F-002-smb-signing.md:5: older-style leftover TODO`, `report.md NOT FOUND: report not checked`, `QA: 2 findings; 2 READY; 0 DRAFT; 1 warnings; 0 errors`, exit 0.
5. **A marker only in `report.md`.** `printf '# Report\n\nTarget: [[HOST]]\n' > report.md`, then a draft run and a `--final` run.
   You should see: the draft run shows no `report.md` line and no new problem (exit 0). `--final` adds `ERROR: report.md:3: leftover marker [[HOST` and `report.md checked: 1 problems`, exit 1. Then `rm report.md`.
6. **A timeline file outside `field-notes/<name>/`.** `cp field-notes/alice/SU-midday.md field-notes/`, then a draft run and a `--final` run.
   You should see: `WARNING: field-notes/SU-midday.md: not in field-notes/<name>/, so it is not in the timeline` in draft (exit 0); the same line as `ERROR` in `--final` (exit 1). `build/interactions-timeline.md` still has only the one row from `field-notes/alice/`. Then `rm field-notes/SU-midday.md`.
7. **`--index`, taken from the root.** `head -n 2 tracker/findings-index.csv > tracker/short.csv` (the header and F-001 only), then `python3 tools/compile.py --root ~/cptc-practice --index tracker/short.csv`.
   You should see: `WARNING: findings/F-002-smb-signing.md:1: F-002 is not in the findings index tracker/short.csv` (exit 0); with `--final` added, the same line as `ERROR` (exit 1). Then `rm tracker/short.csv`.
8. **Paths that lead outside the root are refused.** Each run below prints one `compile failed:` line, exits 2 and leaves `build/` as it was (`ls -l --full-time build` shows the same times before and after):
   - `python3 tools/compile.py --root ~/cptc-practice --index ../cptc-practice/tracker/findings-index.csv` gives `compile failed: path contains '..': ../cptc-practice/tracker/findings-index.csv`
   - `python3 tools/compile.py --root ~/cptc-practice --index ~/findings-index.csv` gives `compile failed: path is outside the root: /home/kali/findings-index.csv -> /home/kali/findings-index.csv`
   - `ln -s / incoming/mallory`, then `python3 tools/compile.py --root ~/cptc-practice`, gives `compile failed: path is outside the root: incoming/mallory -> /`. Then `rm incoming/mallory`.
9. **The git clone is refused.** `cd` into your git clone and run `python3 tools/compile.py --root .`
   You should see: `compile failed: this looks like the git clone (<your clone's full path> has .git); run on the working copy, e.g. ~/cptc-work`, exit 2. It doesn't create `build/` there: `ls build` finds no such folder, unless the clone already had one.

#### `notebook.py`

Covers start-up, the page, checklists, your own files and New file. The fill-in view, autosave, logs and export are built, but their items are still to be added here; the compile button's come when it is built.

**Setup:** step 1 of "Example: a practice run" above makes `~/cptc-practice`. In one terminal, from inside it, start the notebook on a spare port so it can't clash with a real one: `python3 tools/notebook.py --name alice --root ~/cptc-practice --port 8766`. Open `http://127.0.0.1:8766` in Firefox on the same box. Run the commands below in a second terminal, also from inside `~/cptc-practice`. Any item that adds a file removes it again at its end. When you're done, stop the notebook with Ctrl+C (it prints `Notebook stopped.`) and clean up with step 5 of the example.

1. **Options.** `python3 tools/notebook.py --help`
   You should see: `--name` (required), `--root` with the default `~/cptc-work`, `--port` with the default 8765, and no option for the address.
2. **Start-up lines.** In the first terminal, after the start command above.
   You should see: `Notebook: http://127.0.0.1:8766` and `Local only: it listens on 127.0.0.1, so only this box can open it. Ctrl+C stops it.`
3. **The default root is `~/cptc-work`, not the folder you're in.** `HOME="$PWD/manual-test-home" python3 tools/notebook.py --name alice --port 8767`
   You should see: `notebook failed: root folder not found: /home/kali/cptc-practice/manual-test-home/cptc-work`, exit 2.
4. **A name with nothing usable is refused.** `python3 tools/notebook.py --name '!!!' --root ~/cptc-practice --port 8767`
   You should see: `notebook.py: error: argument --name: no letters or digits to make a file name from: '!!!'`, exit 2.
5. **A port already in use.** `python3 tools/notebook.py --name alice --root ~/cptc-practice --port 8766` while the first one runs.
   You should see: `notebook failed: can't listen on 127.0.0.1:8766: ...`, exit 2. The first notebook keeps running.
6. **The git clone is refused.** `cd` into your git clone and run `python3 tools/notebook.py --name alice --root . --port 8767`
   You should see: `notebook failed: this looks like the git clone (<your clone's full path> has .git); run on the working copy, e.g. ~/cptc-work`, exit 2. Then `cd ~/cptc-practice`.
7. **The page.** In Firefox.
   You should see: a left column with `Light / dark`, your files, `New`, `Checklists`, `Logs` and `Export`, and nothing else (no Compile yet). The colours follow your system's light or dark setting; `Light / dark` swaps them.
8. **Checklists and saved ticks.** `md5sum checklists/*.md > ../checklists.md5`. Click `Checklists`, open one, and tick a task. Reload the page and open the same checklist again.
   You should see: every `- [ ]` line as a checkbox and every other line as it is in the file; the tick is still there after the reload; `cat field-notes/alice/checklist-state.json` shows it as `true`. `md5sum -c ../checklists.md5` prints `OK` for every checklist: the checklists themselves never change. Then `rm ../checklists.md5`.
9. **A broken tick file is refused, not overwritten.** `cp field-notes/alice/checklist-state.json ../state.bak`, then `echo '{oops' > field-notes/alice/checklist-state.json`. Open the checklist again and click a checkbox.
   You should see: above the checklist, `field-notes/alice/checklist-state.json can't be read (...)`; the click is undone and the line says `tick not saved: field-notes/alice/checklist-state.json can't be read (...)`; the file still holds `{oops`. Then `mv ../state.bak field-notes/alice/checklist-state.json`.
10. **File content is shown as text, never run.** `printf -- '- [ ] <script>alert(1)</script>\n' > checklists/99-manual-test.md`, then reopen `Checklists` and open it.
    You should see: a checkbox labelled `<script>alert(1)</script>` as plain text, and no pop-up. Then `rm checklists/99-manual-test.md`.
11. **Your own files.** Reload the page.
    You should see: `findings/F-001-default-admin-password.md`, `findings/F-002-smb-signing.md` and `field-notes/alice/SU-midday.md`, sorted by file name so the prefixes group. Then `mkdir -p incoming/bob/findings && cp findings/F-001-default-admin-password.md incoming/bob/findings/` and reload: the teammate's copy isn't listed. Then `ln -s / findings/F-009-x.md` and reload: the column shows `Not listed: path is outside the root: findings/F-009-x.md -> /`. Then `rm -r incoming/bob findings/F-009-x.md`.
12. **New file: the form.** Click `New` and pick each type in turn.
    You should see: the five types (Note, Incident report, Status update, Inject response, Finding); the `Number (NNN)` box only for Incident report and Finding; for Incident report it already holds `001`; `Start from` only for Finding.
13. **New file: an incident report, then the same number again.** Type `Incident report`, title `DB down`, keep `001`, click `Create`. Then click `New` again, type `Incident report`, title `Other`, number `001`, `Create`.
    You should see: `Created field-notes/alice/IR-001-db-down.md`, shown in bold in the left column; the next form suggests `002`; the second file is still created, with `Warning: IR-001 already exists: field-notes/alice/IR-001-db-down.md`.
14. **New file: a finding number already in use.** Type `Finding`, title `SMB signing`, number `001`, `Create`.
    You should see: `Created findings/F-001-smb-signing.md` and `Warning: F-001 already exists: findings/F-001-default-admin-password.md`. The file is made anyway: who gets which ID is the team's call (rule R6).
15. **New file: an existing file is never overwritten.** Repeat item 14 exactly.
    You should see: `refused: already exists, choose a different title: findings/F-001-smb-signing.md`; `cat` shows the file unchanged. Then `rm field-notes/alice/IR-001-*.md findings/F-001-smb-signing.md`.
16. **Requests from anywhere else are refused.** Each command prints one line, and nothing in `~/cptc-practice` changes (`ls -l --full-time field-notes/alice` shows the same times before and after):
    - `curl -s -H 'Host: evil.example:8766' http://127.0.0.1:8766/` gives `refused: use http://127.0.0.1:8766` (a wrong `Host`, as DNS rebinding would send)
    - `curl -s http://localhost:8766/` gives the same line: only the exact address `127.0.0.1:8766` is accepted
    - `curl -s -X POST -d '{"key": "x", "checked": true}' http://127.0.0.1:8766/checklist-state` gives the same line: a change without this run's token
    - `curl -s 'http://127.0.0.1:8766/checklist-view?path=../../etc/passwd'` gives `refused: path contains '..': ../../etc/passwd`
    - `curl -s -i -X PUT http://127.0.0.1:8766/ | head -n 1` gives `HTTP/1.0 501 Not Implemented`: only GET and POST are answered
17. **A title with a line break is refused.** The Title box can't hold one, so send it the way the page does, with this run's token:
    `T=$(curl -s http://127.0.0.1:8766/ | sed -n 's/.*name="cptc-token" content="\([^"]*\)".*/\1/p')`, then `curl -s -X POST -H "X-CPTC-Token: $T" -d '{"type": "Note", "title": "a\nb", "nnn": null, "library": null}' http://127.0.0.1:8766/new-file`
    You should see: `not created: the title must be one line, with no line breaks`, and no new file in `field-notes/alice/`.
18. **The log folder (`$LOGDIR`) is read from the environment and never written.** Stop the notebook (Ctrl+C) and start it again with the log folder pointed into the practice copy: `LOGDIR="$PWD/field-notes/alice" python3 tools/notebook.py --name alice --root ~/cptc-practice --port 8766`. Reload the page, click `New`, pick `Note`, title `log test`, `Create`.
    You should see: `refused: the log folder is read-only, not writing: field-notes/alice/NOTE-log-test.md`, and no new file. Then stop it and start it once more with `env -u LOGDIR python3 tools/notebook.py --name alice --root ~/cptc-practice --port 8766`: the same Note is now created, because the log folder is back to its default, `~/cptc-logs`, outside the practice copy. Then `rm field-notes/alice/NOTE-log-test.md`. The Logs view only reads the log folder.

### Questions Operations might ask

Short answers a teammate can give. `scripts/logged-shell.md` has its own.

#### `compile.py`

- **"Where did this come from?"** (**Unconfirmed** whether AI-assisted code is acceptable; blocked by the open question "Does the 'explain your code' rule cover AI-assisted code?") It was written for this team with AI assistance, from our own design brief. It uses only Python's standard library, and it was reviewed function by function before it was accepted.
- **"Can you explain how it works?"** It was written to be explainable (rule R4): small, plainly named functions, with comments that say why. It was reviewed function by function. The function-by-function walkthrough (each function's line range, what it does, and a short answer for questions like these) is in the public app repo; see the line under "What's here".
- **"Does it touch any target, or send data anywhere?"** No. It imports no networking code. It only reads the team's own Markdown and CSV files inside the working copy (`~/cptc-work` by default), and the only files it writes are the four in `build/`.
- **"Does it run commands?"** No. Nothing in it starts another program. If `pandoc` is installed, it prints the command to convert `report.md`; a person copies it and runs it.
- **"Can it change a teammate's files, or ours?"** It never changes a file it reads: our findings, teammates' files in `incoming/<name>/` (rule R18), the index, the timeline files and `report.md`. The only files it writes are its own four outputs in `build/`, rewritten on every run that isn't refused. Before writing, it checks `build/` and each of its four files, so a link there can't redirect a write into `incoming/` or `report.md`.
- **"What doesn't it check?"** It runs only the checks in "The checks" above: mostly each finding's labelled lines at the top, its reproduction steps, leftover placeholders, and the file names and IDs. It doesn't judge whether a finding is right or complete: not the technical content, not whether the CVSS score matches the vector or the severity, and not whether sections such as Remediation are there. In `report.md` (`--final` only) it looks only for leftover markers and older-style leftovers, and it can't read the exported PDF or DOCX, so the manual checks in `checklists/50-report-qa.md` still apply.

#### `notebook.py`

Answers for what is built today (see "What it does today" above).

- **"Where did this come from?"** (**Unconfirmed** whether AI-assisted code is acceptable; blocked by the open question "Does the 'explain your code' rule cover AI-assisted code?") It was written for this team with AI assistance, from our own design brief. It uses only Python's standard library, and each part was reviewed function by function before it was accepted.
- **"Can you explain how it works?"** It was written to be explainable (rule R4): small, plainly named functions, with comments that say why. It was reviewed function by function. The function-by-function walkthrough (`tools/notebook-breakdown.md`: each function's line range, what it does, and a short answer for questions like these) is in the public app repo; see the line under "What's here".
- **"Is it a server on the network?"** No. It listens only on `127.0.0.1`, so only the box it runs on can open it. The address is written into the code, and there is no option to change it. It also refuses any request whose `Host` isn't exactly `127.0.0.1:<port>`, so a website can't reach it by pointing its own name at `127.0.0.1` (DNS rebinding). It makes no outbound connections, and the page loads nothing from the internet: its styles and script are inside the page.
- **"Is there a login?"** No. It's a single-person tool on your own box, like a text editor. Each run makes a new random token and puts it in its own page; every request that changes something must carry it. That stops other websites open in the same browser (including a client app we are testing) from making changes, because they can't read our page to learn the token. It isn't a password: anyone who can use the box can open the page.
- **"Can a hostile file or log run code in the page?"** No. File content is put into the page as plain text only, never as HTML, so a `<script>` in a file shows as text. Every response except the one app page is plain text or JSON, with headers that stop the browser from treating it as a web page or showing it inside another site.
- **"What does it store, and where?"** Only plain files in the working copy (`~/cptc-work` by default): the `.md` files you create with New (in `findings/` or `field-notes/<yourname>/`) and your checklist ticks in `field-notes/<yourname>/checklist-state.json`. It also saves your own `.md` files there from the fill-in view, the export zip in the working copy's top folder, and a log you copy into `evidence/`. It never changes the checklists, the templates or the findings library, and it never overwrites an existing file when making a new one.
- **"Can logs with secrets leak through it?"** Our terminal logs (`~/cptc-logs/`, or `$LOGDIR`) can hold secrets: passwords, hashes and tokens typed or printed during the test. The Logs view shows them read-only, only on `127.0.0.1` with no outbound connections, and the notebook never writes into the log folder. Export leaves logs out unless "Include logs" is ticked (off by default), and copying a log into `evidence/` copies it unchanged, secrets included. Redact secrets before any log text goes into a finding or the report.
- **"Does it run commands?"** No. Nothing in it starts another program, and a test reads its source to check that it doesn't import subprocess and never uses os.system, os.popen, exec or eval.
- **"Can it change a teammate's files?"** No. Teammates' copies in `incoming/<name>/` are never listed, and every write refuses a path inside `incoming/` (rule R18) or the log folder. It also refuses a folder or file whose link points outside the working copy, and it refuses to start in the git clone.
- **"What's built, and what isn't?"** Built: the checklists, the list of your own files, New file, the fill-in view with autosave, the log viewer and export (one zip). Not built yet: the compile button and the combined Markdown export. Until then, use `compile.py` from the terminal, as "Until then" above says.
