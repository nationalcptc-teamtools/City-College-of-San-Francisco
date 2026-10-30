*Draft, needs review.*

# 4. SNMP Default Community String

- **Phase:** Discovery (no credentials needed)
- **Risk:** 🟢 Safe / 🟡 Noisy / 🔴 Risky: a limited system-information read is Safe; guessing three common strings or walking the full tree is Noisy; any SNMP write is Risky and needs approval every time
- **Tier:** Must know
- **Finding:** library L02 (`snmp-default-community`)
- **Runs on:** Linux appliances, routers, switches, printers, cameras and other SNMP-managed devices
- **Ports:** 161/UDP (SNMP)
- **Tools:** onesixtyone, snmpwalk

## What it is
SNMP lets monitoring systems read device information. Versions 1 and 2c use a shared community string instead of a user login. Many devices ship with `public` for reading and `private` for writing; if either is left at its default, anyone who can reach UDP 161 can use it.

Default SNMP communities did not appear in the reviewed six-environment sample. This playbook is here because it is an explicit safe-recon check with a prepared library entry; that is checklist value, not evidence the weakness occurred historically.

**Checklist:** `checklists/15-linux.md` step 2 (Services: SNMP). Use Recon Field Guide Part 3 and Part 8 (`playbooks/recon/RECON-GUIDE.md`) and library L02 (`snmp-default-community`).

## Commands

1. Build `community.txt` by hand with only `public`, `private` and `community`, one string per line, as required by the Recon Field Guide.
   Expected: A three-line input file; no larger wordlist.
2. Check the three common community strings against one host: `onesixtyone -c community.txt <host>` — 🟡 Noisy. [[NOTE: from the Recon Field Guide]]
   Expected: A responding community string and short device description, or no response.
3. If `public` works, read only the system subtree: `snmpwalk -v2c -c public <host> 1.3.6.1.2.1.1` — 🟢 Safe. [[NOTE: from the Recon Field Guide]]
   Expected: Minimal system name, description, location or uptime information.
4. A full MIB-2 walk, `snmpwalk -v2c -c public <host>`, is 🟡 Noisy and may be slow on small devices. [[NOTE: from the Recon Field Guide]]
   Expected: Broader read-only information only when the extra collection is justified.
5. Do not use an SNMP write operation. [[TODO: Add a client-approved write-validation procedure only if the team later decides it is necessary; any write is 🔴 Risky and needs approval every time, and no write command belongs in this draft.]]
   Expected: Read-only proof is normally sufficient.

## Evidence to capture
- `evidence/F-NNN-01.txt`: the accepted default string and limited system-subtree response.
- Host, source network, timestamp and the exact three-string guess list.
- Redact location, contact or network details not needed to prove the finding.

## Practice
- [[TODO: Choose an isolated SNMPv2c device or simulator and confirm the difference between the limited system subtree and a full walk.]]
- Practise copying the result into library L02 without claiming write access.

---
*Written by the CCSF 2026 team from the Recon Field Guide and past-CPTC environment research.*
