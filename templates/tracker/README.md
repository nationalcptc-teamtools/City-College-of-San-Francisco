# Team Tracker

These are five CSV files that together give the team one shared picture of the engagement. Open them in any text editor, or LibreOffice Calc if it's installed (**Unconfirmed** on the competition boxes; see the open question "What was on the competition boxes?"). The design follows the shared-tracker web apps some finalist teams built, but uses plain files: we need the function, not another app to debug on the day.

**Setup at kickoff:** copy this folder to `~/cptc-work/tracker/`. **The live copies never come back into this repo.** The repo is public, and these files will hold real credentials and client data.

**Sharing method: TBD.** It depends on whether shared storage or a shared document is provided (open question "Is shared storage or a shared document provided?"). Until then, the safe default is one copy per person (`hosts-alice.csv`), with `findings-index.csv` kept on one box only, so no two people edit the same file.

**Cells:** use `;` rather than `,` between multiple values in one cell. A cell must not start with `=`, `+`, `-` or `@` (Calc treats it as a formula).

| File | One row per | Columns worth knowing |
|---|---|---|
| `hosts.csv` | Host | `stage`: `todo` → `enum` → `foothold` → `privesc` → `owned`, or `ot-do-not-touch` (also add those to `exclude.txt` tagged `# OT`). `owner` is who is working it. |
| `credentials.csv` | Credential | `source_finding` is where it came from. `tried_on` / `works_on` list hosts or services, so no one retries blindly or locks an account. In the report, redact `secret` to its first and last characters. |
| `created-accounts-and-artifacts.csv` | Anything we added or changed on a system: accounts, files, services, config changes | `cleaned_up` = `yes` / `no`. This is the cleanup list and the source for report Appendix F. For files, put the SHA-256 in the `sha256` column. |
| `attack-path.csv` | Edge in the attack path (`from` → `to`) | `choke_point` = `yes` when fixing that one finding breaks the path. This becomes the Attack Path diagram in the report. |
| `findings-index.csv` | Finding | The master list of IDs (kept on one box; `compile.py` flags IDs missing from it). `status`: `drafting` / `review` / `done`. QA checks the report against this file. |
