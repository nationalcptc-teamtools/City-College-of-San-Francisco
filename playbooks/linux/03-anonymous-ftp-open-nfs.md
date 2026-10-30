*Draft, needs review.*

# 3. Anonymous FTP and Open NFS Exports

- **Phase:** Discovery (no credentials needed)
- **Risk:** 🟢 Safe / 🟡 Noisy / 🔴 Risky: RPC/NFS export listing is Safe; the permitted anonymous FTP check is Noisy; mounting an export, reading files beyond a minimal sample or testing write access is Risky and needs approval every time
- **Tier:** Must know *(proposed)*
- **Finding:** related library L21 (`cleartext-protocols`) for FTP transport; no dedicated anonymous-file-service entry yet
- **Runs on:** FTP servers, rpcbind and NFS servers
- **Ports:** 21 (FTP), 111 (rpcbind), 2049 (NFS)
- **Tools:** nmap, rpcinfo, showmount; FTP/NFS clients only after an approved procedure exists

## What it is
Anonymous FTP accepts a connection without a user account. An open NFS export tells remote systems which directories are shared and who may use them. Read access can expose backups, scripts and credentials; write access can let someone replace content or plant files another service uses.

Anonymous FTP appeared in two of the six reviewed CPTC environments. In one it exposed administrative transcripts and led to much broader compromise; another report recorded anonymous FTP writes. Open NFS did not appear in the sample; it is here as a standard Linux discovery check, not because it recurred.

**Checklist:** `checklists/15-linux.md` step 2 (Services: FTP and NFS). Use Recon Field Guide Part 3 and Part 8 (`playbooks/recon/RECON-GUIDE.md`); use library L21 (`cleartext-protocols`) only when documenting FTP's cleartext transport separately.

## Commands

1. Run the Linux-port check on one claimed host: `nmap -n -sT -p 21,22,25,111,2049,3306,5432,6379,27017,465,587,873 <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: FTP, rpcbind, NFS and the other listed Linux-service ports are reported open, closed or filtered.
2. Check the permitted anonymous FTP login once: `nmap -n -p 21 --script ftp-anon <host>` — 🟡 Noisy. [[NOTE: from the Recon Field Guide]]
   Expected: The script reports whether anonymous login is accepted and may show a limited listing.
3. List registered RPC programs: `rpcinfo -p <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Registered RPC services and ports are listed.
4. List NFS exports without mounting: `showmount -e <host>` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Export paths and allowed client ranges are displayed.
5. Do not mount an NFS export or read/write FTP/NFS files without approval. [[TODO: Add a reviewed, read-only minimal-sample procedure after the exact command and rating appear in Recon Field Guide Part 3 or 8. Any write test is 🔴 Risky and needs approval every time.]]
   Expected: Evidence is limited to one approved sample and does not alter access times or content where that matters.

## Evidence to capture
- `evidence/F-NNN-01.txt`: `ftp-anon`, `rpcinfo` or `showmount` output with host and timestamp.
- The export path, client restriction and whether anonymous FTP permits only listing, reading or writing.
- Do not claim write access unless it was separately approved and demonstrated; preserve any written approval.

## Practice
- [[TODO: Build an isolated FTP/NFS lab with separate list, read and write permissions and document how the outputs differ without changing production-like files.]]
- Practise reporting exposed filenames and permissions without copying unnecessary sensitive data.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
