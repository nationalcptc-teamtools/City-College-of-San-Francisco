**ICS/SCADA systems**

An industrial control system (ICS) is a general term used to describe a conglomerate of control components that preside over hardware and software aspects of large infrastructure sectors such as power or other discrete manufacturing industries (e.g., automotive). Control in ICS infrastructure can be fully automated or may include a human in the loop (NIST)—this also includes the insertion of additional IT capabilities to supplement aging analog devices and similar mechanical alternatives.

ICSs are extremely vulnerable and carry an enormous risk, so using options like -_sT_ (full connection TCP probe) to limit the intensity of scans is _always_ advisable. If you're someone in charge of managing or protecting an ICS network, the below commands may prove quite useful.

|   |   |
|---|---|
|Detect standard (open) ports|nmap -Pn -sT --scan-delay 1s --max-parallelism 1-p80,102,443,502,1089, 1091,2222,4000,4840, 20000,34962,34964, 34980,44818,47808, 55000,55003 <target>|
|Control system ports (BACnet/IP)|nmap -Pn -sU -p47808 --script bacnet-info <target>|
|Ethernet/IP|nmap -Pn -sU -p44818 --script enip-info <target>|
|Discover a Modbus device|nmap -Pn -sT -p502 --script modbus-discover <target>|
|Discover a Niagara Fox device|nmap -Pn -sT -p1911,4911 --script fox-info <target>|
|Discover a PCWorx device|nmap -Pn -sT -p1962 --script pcworx-info <target>|

**Modbus**

- [mbtget](https://github.com/sourceperl/mbtget): A perl command-line tool to send Modbus/TCP requests

- [modbusclient](https://www.rapid7.com/db/modules/auxiliary/scanner/scada/modbusclient): This is a Metasploit module I created to send Modbus/TCP requests

- [Modbus 0x5a](https://github.com/arnaudsoullie/funwithmodbus0x5a): Tools presented in my [DEFCON ICS Village talk](http://pentesting-ics.com/2018/03/08/yolo/)

- [SMOD](https://github.com/enddo/smod): Modbus Pentesting Framework

- [Modbus-scanner](https://github.com/arnaudsoullie/modbus-scanner): A tool to monitor Modbus values over time

- [https://github.com/arnaudsoullie/modbus-scanner](https://github.com/arnaudsoullie/modbus-scanner)

**S7**

- [snap7](http://snap7.sourceforge.net/): an open-source library to communicate with Siemens PLCs

- [python-snap7](https://github.com/gijzelaerr/python-snap7): Python wrappers to snap7

**Misc**

- [A list of ICS default passwords](https://github.com/arnaudsoullie/ics-default-passwords)

- [SCADAPASS](https://github.com/scadastrangelove/SCADAPASS): Another (bigger) list of ICS default passwords

## Git clone these
**plcscan**

- git clone [https://github.com/meeas/plcscan](https://github.com/meeas/plcscan)

**ICSSecurityScripts**
- git clone [https://github.com/tijldeneut/ICSSecurityScripts](https://github.com/tijldeneut/ICSSecurityScripts)

**Digital Bond's ICS Enumeration Tools**
- git clone [https://github.com/digitalbond/Redpoint](https://github.com/digitalbond/Redpoint)

**Copy Redpoint nmap scripts to the nmap script folder**
- sudo cp Redpoint/*.nse /usr/share/nmap/scripts

**Install modbus-cli**
- sudo gem install modbus-cli

**Download ModbusPal.jar from Sourceforge**
- [https://sourceforge.net/projects/modbuspal/files/modbuspal/RC%20version%201.6b/](https://sourceforge.net/projects/modbuspal/files/modbuspal/RC%20version%201.6b/)

### ICS/SCADA Security Resource
- [https://github.com/w3h/icsmaster](https://github.com/w3h/icsmaster)

**SCADA Passwords**
- [https://github.com/w3h/icsmaster/blob/master/Scada_Password.csv](https://github.com/w3h/icsmaster/blob/master/Scada_Password.csv)

**SCADA Dorks**
- [https://github.com/w3h/icsmaster/blob/master/Scada_Dorks.csv](https://github.com/w3h/icsmaster/blob/master/Scada_Dorks.csv)
- [https://github.com/AustrianEnergyCERT/ICS_IoT_Shodan_Dorks/blob/master/AEC_ICS_IOT_Shodan_dorks.CSV](https://github.com/AustrianEnergyCERT/ICS_IoT_Shodan_Dorks/blob/master/AEC_ICS_IOT_Shodan_dorks.CSV)

**ICS Enumeration Tools**
- [https://github.com/w3h/icsmaster/tree/master/nse](https://github.com/w3h/icsmaster/tree/master/nse)
