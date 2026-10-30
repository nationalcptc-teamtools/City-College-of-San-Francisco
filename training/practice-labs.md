# Self-study practice labs

## Three rules

1. Practise only on machines you own or have explicit permission to test.
2. Put every home target on a host-only VirtualBox or VMware network. Do not bridge an intentionally vulnerable machine to the internet.
3. Log your terminal like we do at the event, then save the useful evidence with your finding.

## If you only have one evening

- **Recon:** Scan `scanme.nmap.org` within its rules, then map Metasploitable 2 without exploiting it.
- **Windows/AD:** Complete the enumeration portion of the hosted AD module before building a home domain.
- **Linux:** Start with OverTheWire Bandit, then write down what each clue proved.
- **Web:** Complete the first PortSwigger Academy learning path that matches your weakest topic.
- **OT:** Run Conpot on a host-only network and stop after read-only identification.
- **AI/LLM:** Complete the introductory Web LLM attacks labs and record the prompt, response and impact.
- **Reporting:** Turn one completed lab into a finding, attach evidence and run the report QA workflow.

## Recon

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| [Nmap `scanme.nmap.org`](https://nmap.org/book/man-examples.html) | Legal, rate-limited service discovery and interpretation of scan output | Free | none | `playbooks/recon/RECON-GUIDE.md` |
| [Metasploitable 2 home lab](https://docs.rapid7.com/metasploit/metasploitable-2/) | Host discovery, port mapping, service identification and handoff without touching a live target | Free | 30 min | `playbooks/recon/RECON-GUIDE.md`; `checklists/15-linux.md` |

## Windows/AD

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| [Active Directory Enumeration & Attacks](https://academy.hackthebox.com/course/preview/active-directory-enumeration--attacks) | Guided domain enumeration, shares, users, BloodHound, AS-REP roasting and Kerberoasting | Paid | none | `playbooks/windows/`; `checklists/10-ad-internal.md` |
| [Retired Windows machines](https://help.hackthebox.com/en/articles/5185338-how-to-play-machines-on-hack-the-box) | Targeted Windows practice with writeups available after the attempt | Free rotation / paid library | none | `playbooks/windows/`; `checklists/10-ad-internal.md` |
| [GOAD MINILAB home lab](https://github.com/Orange-Cyberdefense/GOAD) | A small intentionally vulnerable domain for repeatable enumeration and attack-path practice | Free project; Windows evaluation images | evening | `playbooks/windows/`; `checklists/10-ad-internal.md`; `checklists/40-evidence-and-logging.md` |

## Linux

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| [OverTheWire Bandit](https://overthewire.org/wargames/bandit/) | Linux navigation, SSH, permissions, text processing and clue-driven investigation | Free | none | `playbooks/linux/`; `checklists/15-linux.md` |
| [Metasploitable 2 home lab](https://docs.rapid7.com/metasploit/metasploitable-2/) | Weak services, exposed files, old software and privilege-escalation evidence on an isolated target | Free | 30 min | `playbooks/linux/`; `checklists/15-linux.md`; `checklists/40-evidence-and-logging.md` |

## Web

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| [Web Security Academy](https://portswigger.net/web-security) | Guided labs for authentication, access control, SQL injection, XSS, SSRF, XXE and information disclosure | Free | none | `playbooks/web/`; `checklists/20-web-app.md` |
| [OWASP Juice Shop home lab](https://owasp.org/www-project-juice-shop/) | Repeatable testing of a deliberately insecure application with a broad web finding set | Free | 30 min | `playbooks/web/`; `checklists/20-web-app.md`; `checklists/40-evidence-and-logging.md` |
| [CloudGoat](https://github.com/RhinoSecurityLabs/cloudgoat) | Isolated cloud scenarios for storage exposure, IAM enumeration, assumable roles and privilege escalation | Free project; cloud charges | evening | `playbooks/web/04-public-cloud-storage-app.md`; `playbooks/web/05-cloud-role-anyone-can-assume.md` |

⚠️ **Cloud lab:** Use a dedicated training account, restrict the allowed source address, never mix the lab with real data, and verify that every resource is gone when finished.

## OT

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| [Conpot home lab](https://github.com/mushorg/conpot) | Read-only identification of simulated industrial services and evidence capture without control actions | Free | 30 min | `playbooks/ot/01-unauthenticated-hmi.md`; `playbooks/ot/03-unauthenticated-controllers.md`; `checklists/30-ot-ics-safe.md` |
| Two-zone OT home range using Conpot and a firewall VM | Proving allowed and blocked IT-to-OT paths without scanning an entire control range | Free | evening | `playbooks/ot/04-it-to-ot-reachability.md`; `checklists/30-ot-ics-safe.md` |
| Test-only HMI and file-share home range | One approved login/logout, harmless project files and a hard stop before any control action | Free | evening | `playbooks/ot/02-default-hmi-passwords.md`; `playbooks/ot/05-ot-files-on-shares.md`; `checklists/30-ot-ics-safe.md` |

⚠️ **OT stop rule:** Identification is the exercise. Do not send write, start, stop, reset, upload, download or mode-change requests.

## AI/LLM

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| [Web LLM attacks](https://portswigger.net/web-security/llm-attacks) | Prompt injection, unsafe tool access, indirect injection and evidence from a controlled target | Free | none | `checklists/60-ai-llm.md`; `playbooks/web/` |

## Reporting

| Lab | What it practises | Free or paid | Setup effort | Fits |
|---|---|---|---|---|
| One Academy lab written as a full finding | Turning reproducible web evidence into impact, steps and remediation | Free | none | `templates/finding.md`; `checklists/40-evidence-and-logging.md`; `checklists/50-report-qa.md` |
| Home finding pipeline using Metasploitable 2 or Juice Shop | Discovery handoff, evidence naming, duplicate review, report assembly and QA | Free | 30 min | `templates/finding.md`; `checklists/40-evidence-and-logging.md`; `checklists/50-report-qa.md`; `tools/README.md` |
| Home barcode and QR evidence drill | Handling a harmless generated code as identity data and capturing only the evidence needed | Free | 30 min | `playbooks/general/01-access-and-identity-data.md`; `checklists/40-evidence-and-logging.md` |

**One lab is complete only when the evidence and finding are usable by someone who did not run it.**
