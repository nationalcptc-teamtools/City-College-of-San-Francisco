# Evidence and Logging Sheet

The report is only as good as the evidence. Novices: **this sheet is your main job, and it's worth real points.**

## Team screenshot standard (decide before the event)
- Terminal theme: the default on the competition Kali and Windows boxes, font size: the default (decided Oct 27). Everyone uses the same settings, so screenshots in the report look consistent and stay legible.

## Every session
- [ ] Start `scripts/logged-shell.sh <yourname>`. Every command is captured with a timestamp in the prompt, and `*.cmds.log` gets one line per command (time, exit code, directory, command), which is the quick index for incident reports.
- [ ] Windows box: start every PowerShell window with `Start-Transcript … -IncludeInvocationHeader` (exact commands in `scripts/logged-shell.md`)
- [ ] Windows box: to open a transcript in the notebook's Logs view, copy it to Kali with `scp "$HOME\cptc-logs\*.txt" <your Kali login>@<your Kali IP>:~/cptc-logs/` (needs Kali's ssh server; untested on a real Windows box, see `scripts/logged-shell.md`)
- [ ] Confirm the system clock is correct (`date`)
- [ ] Web lane: keep everything going through Burp. For each finding, save the key request and response (right-click the item → "Copy to file" or "Save item") to `evidence/F-XXX-NN-request.txt` and note the time. Burp Community can't save a project, so whatever you don't save is gone when Burp closes.

## Every finding
- [ ] Take an ID immediately (`F-001`, `F-002`…; how IDs are allocated is **TBD**, R6, blocked by the open question "Is shared storage or a shared document provided?") and announce it so it goes in `findings-index.csv`
- [ ] Create `findings/F-XXX-short-name.md` from the matching `findings-library/` entry, or from `templates/finding.md` if there is none
- [ ] Screenshot showing: **the command, the output, the target IP/hostname, and the clock** in one frame
- [ ] Make it readable in the report: crop to what matters, use a large enough font that the text is legible at page width, and box or arrow the key line
- [ ] Name screenshots `evidence/F-XXX-NN.png`
- [ ] Paste the relevant log lines (with timestamps) into the finding. To find them: look up the time in `*.cmds.log`, then open the full transcript in the notebook's Logs view, or in a terminal with `less -R ~/cptc-logs/<file>.log` (type `/` and a word to search, `q` to quit). A plain text editor shows colour codes as junk; `less -R` displays them properly.
- [ ] Write the reproduction steps **while you remember them**, not at the end

## Credentials
- [ ] Record where each credential came from, which finding it relates to, and where it was used
- [ ] Credentials stay in the competition environment only. Redact them in the report (show the first and last characters).

## Changes made to systems
- [ ] Log every account created, password changed, file dropped, or service touched, with a time and host, so it can be reported and cleaned up

## If something breaks
- [ ] Stop. Note the time. Tell the team.
- [ ] File `templates/incident-report.md` and notify Operations (timing TBD, open question "What do the rules require for incident reports, and how fast?")
