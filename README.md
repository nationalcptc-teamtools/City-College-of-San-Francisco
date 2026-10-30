# City College of San Francisco Cybersec - CPTC 2026

```
                    `.:/+ooooo//-.                                .-//ooooo+/:.`                    
               `-+ydNMh/:-----:oNMmhy+-`                    `-+yhmMNo:-----:/hMNhyo-`               
             /yds/.:Ny       `oNh:  ./shh+.              .+hhs/.  :hNo`       yN/./sdy/             
          `+ds-   `mm`      `dN:        .+hh/``      ``/hh+.        :Nh`      `mm    -ym+`          
         :my.     -Ms       sM:           /NmdddhsyhdddmN/           :Mo       sM-     .yd:         
       `sM+       :Mo       dm`         `hNhyyyyyyyyyyyyhNy.         `md       oM-       +My`       
      `hMM:       `mm..:/++odMs/-`    `omdyyyyyyyyyyyyyyyydmo.    `-/sMdo++/:..mm`       :MMh`      
     `hh+Mo     `:omMMMMMMMMMMMMMNds/sNdyyyyyyyyyyyyyyyyyyyydNs/sdNMMMMMMMMMMMMMmo:`     oM+hh`     
     sm` hN:  `oNMMMMMMMMMMMMMMMMMMMNdyyyyyyyyyyyyyyyyyyyyyyyydMMMMMMMMMMMMMMMMMMMMNo`  :Nd `ms     
    :N-  `sNdsmMMMMMMMMMNNmNMMMMMMMmyyyyyyyyyyyyyNNyyyyyyyyyyyyhmMMMMMMMNmNNMMMMMMMMMmsdNs`  :N:    
    yh     .mMMMMMMMMmo-`  ``:+yNMmmdhyyyyyyyyyyymNyyyyyyyyyyyydmmMNy+-.   `-oNMMMMMMMMm.     hy    
   `md    `dMMMMMMMMs`          smymNNdyyyyyyyyyyNNyyyyyyyyyydNNmyms          `sMMMMMMMMd`    dN`   
   `mM/   yMMMMmydNm+:`         :NyhNyNmyyyyyyyyhMMhyyyyyyyymNyNhyN-         `:+mNdymMMMMs   /Mm`   
    hMN: .MMMMMMNy+/hMNmdo:`    `mhdo+mdNdyyyyyhNMMNhyyyyydNdm+oddd`    `:odmNMh/+yNMMMMMN- :NMh    
    +NyNddMMMMMMMMdhNm+..:sdy/`  ddydsshdNNdhhdNMMMMNdhhdNNdhssdydy  `/hds:..+mNhmMMMMMMMMddNyM+    
    `ms`-sMMMMMMMMd `/yds-..:sms./mhyyyymdyhddhyyyyyyhddhymdyyyyhm/.sms:..-sdh/` dMMMMMMMMs-`sm`    
     :N: .MMMMMMMMM:   `+mMdmmdNN+:NmyyydMdyyyyyyyyyyyyyymMhyyhmN:/NNdmmdMN+`   /MMMMMMMMN- :N:     
      om- sMMMMMMMMNs-   :Ms `/dMM/NMmyhNMMhyyyyyyyyyyyydMMNyymMm:MMd/` sM:   -sNMMMMMMMMs -mo      
       oNhsNMMMMMMMMMMNmmMMM.   sMmMMyydhNMMhyyyyyyyyyyhMMNhdyhMNhMs   .MMMmmNMMMMMMMMMMNohNo       
        :mNs+mMMMMMMMMMMMMMMh`  /NmNNmmhyhMMNyyyyyyyyyhMMNhyddNNMhN/  `hMMMMMMMMMMMMMMm/sNm.        
         `+dh//hNMMMMMMMMMdsM+ /NsNdymMmyydMMNyyyyyyyyNMMdyymMmymmoN: oMsdMMMMMMMMMNh//hd/          
            :yms//odMNys+- oMosm/sNyyhMmyyymNmmyyyyyyNmNmyyyNNyyyMo/msoMo -+syMMdo//sds.            
              `:shNMm+-..-oNMdo`-NdyyymMNdyyNhhyyyyyyhhNyydNMmyyymm.`+dMN+-..-+mMNho-`              
                   `//ossso/.   sNyyyyyhNNdymhNNNmmNNdhdymNNhyyyyyM+   ./+sss++:.                   
                                sNhyyyyydNhyhyhyyNdyyyhhyhNdyyyyyhM+                                
                               :mmNhyyyyyNMmhyhddddddhydmMNyyyyydNmd`                               
                              -NhyyyyyyyyhNMMNmmmmmmmmNMMmyyyyyyyyydh                               
                              `:/+osyyyyyyhNMMMMMMMMMMMMmyyyyyyyyso+o.                              
                                     `..:::+ooossssssooo//::-..`
```

Pre-staged templates, checklists, and scripts for the Collegiate Penetration Testing Competition (CPTC12, Regionals).

## Rules (official rulebook, Oct 2025)

- **This repo is public.** Never put credentials, client data, or anything from the competition environment in here, during or after the event (R3).
- **During competition hours,** teams "may make changes to the content on their repository … from the Competition Environment."
- **Be ready to explain anything in `scripts/` and `tools/`.** How each works: `tools/README.md`.

Source: the [official rulebook](https://cp.tc/docs/cptc-rules.pdf).

## Start here

1. `CONVENTIONS.md`: team rules (R1–R18) and naming.
2. `WORKFLOWS.md`: what to do, in what order.
3. `checklists/00-kickoff.md`: kickoff.

## Layout

| Path | What it is |
|---|---|
| `checklists/` | Run sheets: `00` kickoff, `10` AD, `15` Linux, `20` web, `30` OT-safe, `40` evidence, `50` report QA, `60` AI/LLM |
| `playbooks/` | Per-technique steps: `windows`, `web`, `linux`, `ot`, `general`, `ai`, `recon`. Start at `playbooks/README.md` |
| `TOOLS.md` | Tools we use, and what to install if the box is minimal |
| `templates/` | Finding, report (`.md` and `.docx`), severity, incident, status, inject, tracker CSVs. Marker key: `templates/README.md` |
| `findings-library/` | Pre-written findings. Copy one into `findings/` on the day |
| `scripts/`, `tools/` | Logged shell, `pull.sh`, `compile.py`, `notebook.py`. How to run each: `tools/README.md` |
| `training/` | Study material, practice labs |
| `archive/` | 2025 repo, kept as is (tag `archive/pre-2026`) |
| `findings/`, `evidence/`, `field-notes/`, `incoming/`, `build/` | Event files. Live in the working copy, never committed |

## On the day

1. Kickoff: read scope and ROE aloud, write the out-of-scope list on the whiteboard.
2. Make your working copy (below), start a logged shell in it: `scripts/logged-shell.sh <yourname>`. Optionally start the notebook.
3. Give each finding the next free ID in your block before further testing. At kickoff, each person gets 20 IDs in order, writes the block on the whiteboard, and never reuses an ID (R6).
4. Finder fills `templates/finding.md` (or a library entry) and hands it to the report writer, who adds its row to `tracker/findings-index.csv`. Author edits their own file until it is pasted into `report.md`; after that, edit `report.md` (R18). Severity gets one review pass (R8).
5. If something breaks: stop, tell the team, and file `templates/incident-report.md`. Deadline is **TBD**.
6. Report assembly starts at the halfway point. The report writer copies `templates/report.md` to `~/cptc-work/report.md`.
7. Before each submission, someone who didn't write it runs `checklists/50-report-qa.md`.

## Working copy and moving files on the day

Work in a copy, never in the git clone. At kickoff, each person runs:

```
<repo-clone>/scripts/make-workcopy.sh <yourname> <repo-clone>
```

- `<yourname>`: lowercase letters, digits, `-` (e.g. `alice`).
- Copies only **committed** files into `~/cptc-work`, with no `.git`. Run `git status` in the clone first.
- Refuses to run if `~/cptc-work` exists. Needs `git`, no `sudo`.
- **Open every terminal in `~/cptc-work`.** Checklists write scan output to the current directory.
- Tool fix mid-event: copy the one file, e.g. `cp <repo-clone>/tools/compile.py ~/cptc-work/tools/`.

## Notebook

A local web page for your checklists, files and notes. Start it inside the working copy:

```
python3 tools/notebook.py --name <yourname>
```

Open the address it prints. It:
- **Checklists:** not todos, but guides.
- **Your files:** list `findings/` and `field-notes/<yourname>/`, make new ones from the templates, fill in the `[[markers]]` with autosave.
- **Logs:** read your terminal logs, with search.
- **Export:** one zip of your files for the report writer.

Local only (`127.0.0.1`). The rest of the workflow works without it. Details: `tools/README.md`.

## Getting files to the report writer

Use the first that works. Files land in `~/cptc-work/incoming/<name>/`.

1. **Shared storage from the officials**, if offered.
2. **`scripts/pull.sh`** over SSH, run by the report writer in `~/cptc-work`:
   ```
   scripts/pull.sh --setup    # once: each teammate's name, login, IP
   scripts/pull.sh            # pull everyone
   scripts/pull.sh alice      # pull one
   ```
   Each teammate first changes the default `kali` password, starts ssh (`sudo systemctl start ssh`) and has `rsync`. Details and failures: `tools/README.md`.
3. **Export zip**, moved by hand (RDP drive, `scp`). Unpack fresh each time:
   `rm -rf ~/cptc-work/incoming/alice && unzip <file> -d ~/cptc-work/incoming/alice/`

`incoming/` is a read-only mirror. Nobody edits it; every pull overwrites it. Fix a finding in its author's `findings/`, or in `report.md` once pasted.

**Rules check:** external private storage and peer-to-peer file sharing are banned. Copying between our own boxes inside the environment is fine (`sftp`/`rsync` confirmed). Never move event data outside the environment.
