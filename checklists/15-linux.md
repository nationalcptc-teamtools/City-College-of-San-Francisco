*Draft, needs review.*

# Linux Run Sheet

> Risk key and the full playbook list: `playbooks/README.md`. Discovery commands and their ratings: `playbooks/recon/RECON-GUIDE.md` Part 3 (cheat sheet: Part 8.4).
> Every target is a claimed host in `scope.txt`; never type a range.
> ⚠️ Embedded Linux (cameras, kiosks, routers, building controllers) breaks more easily than a server. Treat it as OT-adjacent (Recon Field Guide 3.6).

## 1. Discovery (hand-off from the Recon Field Guide)
- [ ] 🟢 Safe. Linux ports on each claimed host: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` [[NOTE: from the Recon Field Guide]]
- [ ] 🟢 Safe. SSH banner, once: `nc -nv <host> 22`, Ctrl-C after the banner [[NOTE: from the Recon Field Guide]]; then `ssh-audit <host>` [[NOTE: from the Recon Field Guide]] (playbook: playbooks/linux/07-outdated-linux-software.md)
- [ ] 🟡 Noisy. Version of one open port: `nmap -n -sV -p <port> <host>` [[NOTE: from the Recon Field Guide]] (playbook: playbooks/linux/07-outdated-linux-software.md)
- [ ] Web ports (80, 443, 8080, 8443, 9000): hand to the Web lane (`checklists/20-web-app.md`)

## 2. Services
- [ ] 🟡 Noisy. Database banners: `nmap -n -sV -p 3306,5432,6379,27017 <host>` (Recon Field Guide 3.3, step 13) (playbook: playbooks/linux/01-default-database-auth.md)
- [ ] 🟢 Safe. Redis without a password: `nc -nv <host> 6379`, type `PING`, then disconnect [[NOTE: from the Recon Field Guide]]. `+PONG` = **finding**. No other Redis command. (playbook: playbooks/linux/01-default-database-auth.md)
- [ ] 🟡 Noisy / 🔴 Risky. Blank or default database password: check the lockout policy first, then one attempt only. Reading tables or changing data is 🔴 Risky: approval every time. (playbook: playbooks/linux/01-default-database-auth.md)
- [ ] 🟢 Safe. A credential found elsewhere (file, database, other host): one SSH login to check it, then disconnect. Record where it came from. (playbook: playbooks/linux/02-weak-ssh-admin-passwords.md)
- [ ] 🟡 Noisy / 🔴 Risky. Blank, default or guessed SSH/admin passwords: only after the lockout check (same rule as `checklists/10-ad-internal.md` step 2). Login guessing tools (`hydra`, nmap `*-brute`) are 🔴 Risky: stop and ask. (playbook: playbooks/linux/02-weak-ssh-admin-passwords.md)
- [ ] 🟡 Noisy. Anonymous FTP: `nmap -n -p 21 --script ftp-anon <host>` [[NOTE: from the Recon Field Guide]] (playbook: playbooks/linux/03-anonymous-ftp-open-nfs.md)
- [ ] 🟢 Safe. RPC and NFS exports: `rpcinfo -p <host>` [[NOTE: from the Recon Field Guide]], `showmount -e <host>` [[NOTE: from the Recon Field Guide]]. A world-readable export = **finding**. Mounting an export or writing to FTP/NFS is 🔴 Risky: ask first. (playbook: playbooks/linux/03-anonymous-ftp-open-nfs.md)
- [ ] 🟡 Noisy. SNMP community check: build `community.txt` by hand (`printf 'public\nprivate\ncommunity\n' > community.txt`, three guesses only), then `onesixtyone -c community.txt <host>` [[NOTE: from the Recon Field Guide]] (playbook: playbooks/linux/04-snmp-default-community.md)
- [ ] 🟢 Safe. If `public` works, read the system subtree only: `snmpwalk -v2c -c public <host> 1.3.6.1.2.1.1` [[NOTE: from the Recon Field Guide]]. A full walk (no OID) is 🟡 Noisy; `snmpset` is 🔴 Risky: never without approval. (playbook: playbooks/linux/04-snmp-default-community.md)

## 3. On the host (after a login)
- [ ] 🟢 Safe / 🔴 Risky. Secrets in files the current account can already read: configs, private keys, shell history, backups, TLS keys. One login to check a recovered credential is 🟢 Safe; changing permissions, replacing keys or running found scripts is 🔴 Risky. (playbook: playbooks/linux/05-secrets-in-files.md)
- [ ] 🟢 Safe / 🔴 Risky. Privilege escalation, read-only: sudo rules, unusual SUID files, writable cron-controlled paths, Docker group or socket. Using any of them (running the privileged command, writing the cron file, getting root) is 🔴 Risky: approval every time. (playbook: playbooks/linux/06-linux-privilege-escalation.md)

## 4. Outdated software
- [ ] 🟢 Safe / 🔴 Risky. Check each exact version offline against vendor support dates and vulnerability records, and allow for backports. A version alone is Suspected, not proven. Any exploit check is 🔴 Risky: approval every time. (playbook: playbooks/linux/07-outdated-linux-software.md)

## Evidence for every step
Timestamped command + output + screenshot → `evidence/F-XXX-NN.png`. Redact passwords, keys and personal data.
