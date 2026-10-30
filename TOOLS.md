Check your competition Kali box against this list at kickoff.

# Tools

| Tool | What it's for | Used by |
|---|---|---|
| Nmap | Discovers hosts, ports, services, and selected service details. | `checklists/`, `playbooks/recon/`, `playbooks/windows/`, `playbooks/web/`, `playbooks/ot/` |
| Burp Suite Community | Intercepts and manually tests web requests and responses. | `checklists/20-web-app.md`, `playbooks/web/` |
| curl | Makes HTTP requests to fetch and check web content. | `playbooks/recon/`, `playbooks/web/`, `playbooks/general/` |
| WhatWeb | Identifies web technologies and server characteristics. | `playbooks/recon/`, `playbooks/web/` |
| httpx-toolkit | Checks which web addresses respond and shows title, status and technology. Installed as `httpx-toolkit` on Kali; plain `httpx` is a different tool. | `playbooks/recon/`, `playbooks/web/`, `playbooks/general/` |
| gowitness | Takes screenshots of web pages. Not in `kali-linux-default`. | `playbooks/recon/` |
| Gobuster | Discovers web paths, virtual hosts, and DNS names from wordlists. | `playbooks/recon/`, `playbooks/web/` |
| Nikto | Checks web servers for known unsafe files and settings. Only when approved. | `playbooks/recon/`, `playbooks/web/` |
| sslscan | Lists supported TLS protocols, ciphers and certificate details. | `playbooks/recon/`, `playbooks/web/` |
| SecLists | Wordlists for discovery, authentication testing, and fuzzing. | `playbooks/recon/`, `playbooks/web/` |
| NetExec | Runs scoped SMB and Active Directory enumeration and validation. | `checklists/10-ad-internal.md`, `playbooks/recon/`, `playbooks/windows/` |
| Impacket | Windows protocol utilities for enumeration and authorized validation. | `checklists/10-ad-internal.md`, `playbooks/windows/` |
| Evil-WinRM | Connects to authorized Windows Remote Management sessions. | `checklists/10-ad-internal.md`, `playbooks/windows/` |
| enum4linux-ng | Enumerates information exposed by Windows and Samba services. | `playbooks/recon/`, `playbooks/windows/` |
| smbclient | Browses and transfers files through SMB shares. | `playbooks/recon/`, `playbooks/windows/` |
| OpenLDAP client utilities | Queries LDAP directories for users, groups, computers, and configuration. | `checklists/10-ad-internal.md`, `playbooks/recon/`, `playbooks/windows/` |
| BloodHound CE and collector | Maps authenticated Active Directory relationships and attack paths. | `checklists/10-ad-internal.md`, `playbooks/windows/` |
| Net-SNMP | Queries SNMP data for host, service, and device enumeration. | `playbooks/recon/` |
| onesixtyone | Enumerates SNMP devices and community strings. | `playbooks/recon/` |
| PEASS-ng | Enumerates local privilege-escalation paths on Linux and Windows hosts. | `playbooks/general/`, `playbooks/windows/` |
| pspy | Watches Linux processes without elevated privileges. | `playbooks/general/` |

## If the box is minimal

Draft, needs review. Check at kickoff: `for t in rsync zsh nmap nxc curl jq tmux; do command -v $t >/dev/null || echo "missing: $t"; done` and `ls /usr/share/wordlists`.
Installing needs internet, which the event network may not have. Know this list before game day.

| What | Why | How (Debian/Kali package) |
|---|---|---|
| rsync | `scripts/pull.sh` needs it on every box | `sudo apt install rsync` |
| zsh as the login shell | `logged-shell.sh` auto-start goes in `~/.zshrc` | `chsh -s /usr/bin/zsh`, then log out and back in |
| zsh autosuggestions and syntax highlighting | Faster, fewer typos | `sudo apt install zsh-autosuggestions zsh-syntax-highlighting` |
| Wordlists and SecLists | Gobuster, the web playbooks, password cracking. Past events: simple lists like `rockyou.txt` are enough; the point is to try. Small lists are also faster and quieter | `sudo apt install wordlists seclists`; `rockyou.txt` ships gzipped: `sudo gunzip /usr/share/wordlists/rockyou.txt.gz` |
| tmux, jq, curl | Split panes, read JSON, fetch pages | `sudo apt install tmux jq curl` |
| Not in `kali-linux-default` | Wordlists, SMB enumeration, screenshots, fast port scan | `sudo apt install seclists enum4linux-ng gowitness rustscan` |
| Everything else above in one go | The standard Kali tool set | `sudo apt install kali-linux-default` (large download) |

## Our own tools

| Tool | What it's for |
|---|---|
| `tools/compile.py` | Turns findings into report-ready Markdown and runs quality checks. |
| `tools/notebook.py` | A local web page: open and tick the checklists, list your own files, make new files from the templates, fill them in with autosave, read your terminal logs, and export one zip. Not built yet: compile button. |
| `scripts/logged-shell.sh` | Logs the terminal session for evidence and review. |
