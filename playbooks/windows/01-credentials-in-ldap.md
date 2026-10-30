*Draft: command steps not filled in yet.*

# 1. Credentials Exposed in LDAP

- **Phase:** Initial access (no credentials needed)
- **Risk:** 🟡 Noisy: the anonymous query stands out in the DC's logs (matches `checklists/10-ad-internal.md`). Read-only queries with a domain login and one login to check a recovered password are 🟢 Safe.
- **Tier:** Must know
- **Finding:** library L01 (`anonymous-smb-ldap-access`)
- **Runs on:** domain controllers; Windows servers running AD DS; Global Catalog servers
- **Ports:** 389 (LDAP), 636 (LDAPS), 3268 (Global Catalog), 3269 (Global Catalog over TLS)
- **Tools:** nmap, ldapsearch, ldapdomaindump

## What it is
LDAP reads Active Directory's directory of users, groups and computers. Some domain controllers accept an **anonymous bind**: anyone on the network can read parts of it without logging in.

It gets serious when a password sits in a user's attributes: admins sometimes put one in the description field, or a legacy application stores one in its own attribute. Encoded values (base64, for example) count as exposed; encoding is not encryption.

Ports 3268/3269 are the **Global Catalog**, a read-only copy of the whole forest's directory. If 389 returns little, try these.

Related: #13 (secrets in AD comments) is the same idea, but needs a login first.

## Commands


1. Try first: `nmap -Pn -sV -p 389,636,3268,3269 --script ldap-search,ldap-rootdse,ldap-novell-getpass <TARGET_IP>` [[NOTE: from 2024, not yet checked]]
2. Try second: `ldapsearch -x -H ldap://<TARGET_IP>:3268 > ldap1.txt` [[NOTE: from 2024, not yet checked]]
3. Try third: `ldapsearch -x -H ldap://<TARGET_IP>:3268 -b "dc=<CHANGE>,dc=<CHANGE>" > ldap2.txt` [[NOTE: from 2024, not yet checked]]
4. Drill down: `ldapsearch -x -H ldap://<TARGET_IP> -b "ou=Users,ou=<CHANGE: OU from the previous query>,dc=<CHANGE>,dc=<CHANGE>"` [[NOTE: from 2024, not yet checked]]

## Once a credential is found
- Check that it works with a single login. Mind the lockout policy (#26) before trying more than one.
- Pass it to the team: it's the first credential for the authenticated playbooks.

python3 ldapdomaindump.py --user Cascade\\USER --password $PASS$ ldap://<TARGET_IP>:3268


## Evidence to capture
- `evidence/F-NNN-01.png`: the query output showing the attribute that holds the password. Redact the password so only the first and last characters show (`templates/finding.md`).
- The logged command with its timestamp.

## Practice
- **HTB box:** Cascade (retired)
- **Walkthrough:** https://juggernaut-sec.com/hackthebox-cascade/
- **Tip from 2024:** on Cascade, the passwords only show up when the search base names the right organizational unit, down to the users' OU.
- **Practice credentials (practice data only, never use on game day):** [[TODO: move the Cascade username and password from the 2024 `ldapdomaindump` line here]]

---
*Adapted from the CCSF 2024 Windows playbooks. Updated by the CCSF 2026 team.*
