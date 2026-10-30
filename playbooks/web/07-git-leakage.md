*Draft: command steps not filled in yet.*

# 7. Exposed .git Folder

- **Phase:** No credentials (content discovery)
- **Risk:** 🟡 Noisy: finding it takes content discovery (many requests). Downloading the folder once it's found is 🟢 Safe.
- **Tier:** Must know
- **Finding:** none in the library yet
- **Ports:** 80, 443
- **Tools:** A content-discovery tool, git, a git-dumping tool
- **You need:** nothing

## What it is
A site deployed with its `.git` folder left in place lets anyone download the repository: the code, the history, and any passwords or keys ever committed.

**Fix to recommend:** block web access to `.git` (the 2024 doc gives a one-line web-server rule), and rotate any secret found in the history.

## Commands
Git files can be publicly accessible if incorrectly configured. A “.git” directory  found on a web-server which allowed public access could aquite to the configuration files, internal infrastructure infromation, etc. Additionally, attackers can download the directory and use git commands to access logs, commit history, and the files in the repository.


## Evidence to capture
- `evidence/F-NNN-01.png`: the `.git` folder answering in the browser.
- `evidence/F-NNN-02.png`: any secret found in the history, redacted.

## Practice
- [[TODO: none in the 2024 doc; add a box or local setup]]

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
