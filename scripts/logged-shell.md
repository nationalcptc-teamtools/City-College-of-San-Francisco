# `logged-shell.sh`: what it does and how it works

## Why it exists

`logged-shell.sh` gives every tester's terminal an automatic, timestamped record of what was typed and what came back. That record is the source for four things:

1. **Reproduction steps.** Judges marked down 10 of 12 CPTC10 finals reports for weak reproduction steps. With a log you copy the exact command and output instead of reconstructing them from memory hours later.
2. **Incident reports.** The rulebook asks for source and destination, activity timelines and what was affected. If something breaks, the log shows exactly what we ran, against what, and when.
3. **Answering the client.** Finalists were asked mid-event about data exfiltration, account lockouts and network load. A log lets you say precisely what we did or didn't do.
4. **Cleanup.** It's a backup record of anything we created or changed. The primary list is `templates/tracker/created-accounts-and-artifacts.csv`.

It's a recording tool only. It doesn't scan, attack or touch any target.

## What it records

Each session writes two files to `~/cptc-logs/` (or `$LOGDIR` if set):

| File | Contents | Use it for |
|---|---|---|
| `<name>_<UTC time>.log` | **Full transcript**: everything typed and everything printed, including output from SSH or WinRM sessions opened inside it | Exact output for evidence and reproduction steps |
| `<name>_<UTC time>.cmds.log` | **Command index**: one line per local command | Quickly finding *when* something happened, then looking it up in the transcript |

A command index looks like this:

```
2026-11-07 14:02:11 PST (exit 0) [/home/kali/scan] nmap -sn -PE -iL scope.txt -oA disc-icmp
2026-11-07 14:05:40 PST (exit 1) [/home/kali/scan] nxc smb 10.0.1.5 -u guest -p ''
```

The prompt in the transcript also carries a timestamp, so any screenshot of the terminal shows the time as well.

## What it does NOT capture

- **Terminals not started with this script.** Each terminal tab or tmux pane needs its own `logged-shell.sh`.
- **GUI tools**, such as Burp or the browser. For the web lane, see the Burp line in `checklists/40-evidence-and-logging.md`.
- **Commands inside a remote shell, in the index.** If you `ssh` or `evil-winrm` into a box, the index records only the `ssh` / `evil-winrm` command itself. Everything you do on the remote host is still in the full transcript.
- **Your zsh setup.** Kali's default shell is zsh, but this session runs **bash**, so zsh aliases and plugins won't be there. Your `~/.bashrc` is loaded.

## How to use it

```
cd ~/cptc-work                        # your working copy, never the git clone
chmod +x scripts/logged-shell.sh      # once, if it isn't executable
scripts/logged-shell.sh alice         # start a logged session named "alice"
# ... work as normal ...
exit                                  # stop logging; the file paths are printed
```

The name must use lowercase letters, digits and `-`, starting with a letter or digit (e.g. `alice`); any other typed name is refused with a one-line message and nothing is logged, so a name like `../x` can't put logs outside `~/cptc-logs/`. If you leave out the name, it uses the name `make-workcopy.sh` saved in `~/cptc-work/.cptc-name`. If that file is missing or doesn't hold one valid name, it uses your login and prints a one-line warning. Logging still starts, because an unlogged terminal can't be redone and a wrongly named log can be renamed with `mv`.

**Work inside `~/cptc-work`, not the git clone.** The checklists write scan output (host lists, hash files) to the current directory. In the clone, a stray `git add` would publish it. The logs themselves go to `~/cptc-logs/`, outside both.

## Optional: start logging automatically in every terminal

If someone forgets to start the script, that terminal isn't logged. To make it automatic, add this block to the end of `~/.zshrc` on each Kali box at kickoff. Kali's terminals start zsh, so `~/.zshrc` runs every time a new terminal, tab or tmux pane opens.

```
# --- CPTC: start every new terminal inside logged-shell.sh ---------------
CPTC_LOGGER="$HOME/cptc-work/scripts/logged-shell.sh"        # inside the working copy, never the git clone
CPTC_NAME="alice"                                          # your name, for the log filenames
if [[ -o interactive && -z "${CPTC_NOLOG:-}" ]]; then
  if [[ -x "$CPTC_LOGGER" ]]; then
    cd "$HOME/cptc-work" && "$CPTC_LOGGER" "$CPTC_NAME"
    print -P "%F{red}LOGGING STOPPED: this terminal is no longer logged. Close it, or run $CPTC_LOGGER again.%f"
  else
    print -P "%F{red}NOT LOGGED: $CPTC_LOGGER is missing or not executable (chmod +x it).%f"
  fi
fi
# -------------------------------------------------------------------------
```

How it works:
- `[[ -o interactive ]]` runs it only for terminals a person types into, not for scripts or `scp`.
- `-x "$CPTC_LOGGER"` is a safety check. If the path is wrong or the file isn't executable, you get a normal shell instead of a broken one, plus a red **NOT LOGGED** warning so it's never silent.
- `cd "$HOME/cptc-work"` starts the logged session inside the working copy, so scan output lands there, not in your home folder.
- **It doesn't loop.** The script starts *bash*, which reads `~/.bashrc`, not `~/.zshrc`, so the block doesn't run again inside the logged session.
- **When you type `exit`,** the logged session ends and you drop back to plain zsh, with a red warning that you're no longer logged. That's on purpose: if anything ever goes wrong with the script, you still have a working terminal instead of one that closes immediately.
- **To get one unlogged terminal deliberately,** run `CPTC_NOLOG=1 zsh`. That should be rare, and the team should know about it.
- **Set `CPTC_NAME`.** Every competition Kali box may log in as the same user (`kali`), so without a name, everyone's logs would carry the same name.
- **Remove the block after the event.** It changes the competition box's shell config, so add and remove it deliberately.

This block hasn't been tested in zsh yet. Try it once on your own Kali VM before relying on it.

## On the Windows box

The script is Linux-only. PowerShell has a built-in equivalent. Run this at the start of every PowerShell window:

```
New-Item -ItemType Directory -Force "$HOME\cptc-logs" | Out-Null
function prompt { "[$(Get-Date -Format 'HH:mm:ss')] PS $(Get-Location)> " }
Start-Transcript -Path "$HOME\cptc-logs\alice_$(Get-Date -Format yyyyMMddTHHmmss).txt" -IncludeInvocationHeader
```

The `prompt` line changes the PowerShell prompt to `[14:02:11] PS C:\Users\alice>`: the time (24-hour) the prompt appeared, after the previous command finished. The transcript records the prompt in front of each command, so in the transcript and in any screenshot of the window each command carries the time its prompt appeared, as on Kali. It changes only how the prompt looks and records nothing by itself. `-IncludeInvocationHeader` adds a start time above each command, which gives you the same timestamps as the Kali command index. `Stop-Transcript`, or closing the window, ends it. It records only PowerShell windows, not `cmd.exe` and not GUI or RDP actions; screenshot those. To make it automatic, put the same three lines in your PowerShell profile (`notepad $PROFILE`). As with the zsh block, add it at kickoff and remove it afterwards.

To open a transcript in the notebook's Logs view, copy it to `~/cptc-logs` on your Kali box with the `scp` built into Windows (from Windows 10 version 1809): `scp "$HOME\cptc-logs\*.txt" <your Kali login>@<your Kali IP>:~/cptc-logs/`. It needs the ssh server running on your Kali box (as `scripts/pull.sh` needs on each teammate's box), and it is untested on a real Windows box so far: check it at the next Windows practice.

## Line by line

**Lines 1–6: header.** `#!/usr/bin/env bash` runs the script with bash. The comments say what it does and how to use it.

**Line 7: `set -euo pipefail`.** This is a safety switch. The script stops on any error (`-e`), on a typo'd variable name (`-u`), or if any part of a pipeline fails (`pipefail`).

**Lines 9–45: choosing the name (`pick_name`).**
- Line 19 sets the rule once, for a typed name and a saved one alike. A typed name that passes it wins. One that doesn't gets a one-line message and `return 1`, and line 48's `|| exit 1` stops the script there, before the log folder or any log is made. It's printed with `printf '%s\n'` rather than `echo`, because `echo` treats some words as its own options.
- Otherwise it reads `~/cptc-work/.cptc-name`, written by `make-workcopy.sh`, if it is a readable file (`-f` and `-r`; otherwise bash would print its own error). The first `read` takes line one, and still fills `saved` when that line has no final newline. A second `read` must find nothing at all: any further line, even an empty one, makes the saved name invalid, so the file holds exactly one name.
- The rule is the one `make-workcopy.sh` uses: lowercase letters, digits and `-`, starting with a letter or digit. `local LC_ALL=C` makes `[a-z]` mean only the 26 ASCII letters (in some locales it also matches accented ones). Line 48 runs `pick_name` inside `$(...)`, a separate subshell, so the setting never reaches the logged shell, which keeps your own locale; `local` also limits it to this function.
- If there's no valid saved name, it prints a one-line warning and uses `whoami`, your login. On the event boxes that may be `kali` for everyone, so name the logs yourself next time.

**Lines 47–52: setup.**
- `LOGDIR="${LOGDIR:-$HOME/cptc-logs}"` uses `$LOGDIR` if you set one, otherwise `~/cptc-logs`.
- `name="$(pick_name "${1:-}")"` is the session name from lines 9–45; if `pick_name` refused a typed name, `|| exit 1` ends the script here.
- `ts=...` is the start time in UTC, so filenames sort correctly and never collide across timezones.
- `log` and `cmdlog` are the two output file paths. `mkdir -p` creates the folder if needed.

**Lines 54–77: write a startup file for the new shell.** The script starts a *new* bash shell, and that shell needs extra settings. `mktemp` makes a temporary file, and the `cat >"$rc" <<EOF … EOF` block (a "heredoc") writes those settings into it.

> **The tricky part is the `\$` signs.** Because the heredoc's `EOF` isn't quoted, the shell fills in `$variables` as it writes the file. We want that for exactly one value: `$cmdlog` on line 58, so the new shell knows where to write. Everything else must be evaluated later, by the new shell each time it runs, so it's written as `\$` and lands in the file as a plain `$`. The same idea explains the `\\1` and `\\n`, which come out as `\1` and `\n`.

What the new shell gets:
- **Line 57:** it loads your normal `~/.bashrc` first, so your usual bash settings still apply.
- **Line 58:** `CPTC_CMDLOG` holds the index file's path.
- **Line 59:** `HISTTIMEFORMAT` makes bash's history store a timestamp for each command.
- **Line 60:** `HISTCONTROL=` (empty) turns off history filtering. Kali's default ignores repeated commands and ones typed with a leading space; we want everything.
- **Lines 64–74: the `__cptc_log` function,** which runs before every new prompt (that is, after every command):
    - `local code=$?` **must come first.** `$?` holds the exit code of the command you just ran, and any other command would overwrite it.
    - `history 1` gets the last history entry, for example `  42  2026-11-07 14:02:11 nmap ...`.
    - The first `sed` pulls out the history number (`42`). The second strips the number and timestamp, leaving just the command.
    - The `if` writes a line only when the history number has changed since last time. That's how an empty Enter press, which reruns the function with no new command, adds nothing. `__cptc_ready` skips the very first prompt, so an old command from a previous session isn't logged.
    - `printf … >> "$CPTC_CMDLOG"` appends one line: time, exit code, directory, command.
- **Line 75:** `PROMPT_COMMAND=__cptc_log` is a bash feature: bash runs this before printing each prompt. If your `.bashrc` already set a `PROMPT_COMMAND`, this replaces it for the session.
- **Line 76:** `PS1` is the prompt itself: `[date time zone] user@host:dir$`. It's what makes the timestamp appear in every screenshot.

**Lines 79–82: start recording.** `script` is a standard Linux tool (util-linux) that records a terminal session to a file.
- `-q` suppresses its start and stop banners.
- `-f` writes to disk after every output. If the machine crashes, the log is still current.
- `-c "bash --rcfile '$rc'"` runs a new bash that uses our startup file, and `script` records everything in it.

**Lines 83–85: clean up.** After you type `exit`, the temporary startup file is deleted and the two log paths are printed.

## Questions Operations might ask (and short answers)

- **"Does this touch any target?"** No. It only records our own terminal to local files.
- **"Does it send data anywhere?"** No. There's no network activity; both logs stay on the machine where it ran.
- **"Where did this come from?"** (**Unconfirmed** whether AI-assisted code is acceptable; blocked by the open question "Does the 'explain your code' rule cover AI-assisted code?") It was written with AI assistance, and the team has reviewed it and can explain every line (see the walkthrough above). The design (per-command log with exit codes) is based on public CPTC team material, but none of their code is used.
- **"Why bash and not zsh?"** `PROMPT_COMMAND` and `history 1` are bash features, and one shell keeps it simple enough to explain.

## Handling the logs

**The logs will contain secrets.** Every password typed on a command line (`-p 'Password1'`) ends up in both files. Treat them like the credentials tracker:
- They stay inside the competition environment.
- They never get committed to the repo.
- When you quote them in the report, redact them to the first and last characters.
