# Report QA Checklist (before every submission)

> Run this on the **exported file** (PDF/DOCX) as well as the Markdown source. Whenever possible, the person running it should not be the one who wrote the section. Most items here come from criticisms CPTC10 judges made of finalist reports.

## 1. Leftovers (zero hits allowed)
- [ ] Run these from inside `~/cptc-work`.
- [ ] Run `python3 tools/compile.py --final` first: fix every `ERROR` (it exits 1 while any is left) and check every `WARNING`. It runs its checks on the finding files (`findings/`, `incoming/*/findings/`), the `IR-`/`SU-`/`INJ-` files and the findings index (`tracker/findings-index.csv`, or `--index PATH`), but reads `report.md` only for leftover markers and older-style leftovers, and never reads the exported file, so the items below still apply. Earlier in the event, draft mode (`python3 tools/compile.py`, without `--final`) shows the same problems as warnings, without the `report.md` checks. Details: `tools/README.md`.
- [ ] No template markers remain: `grep -rnE '\[\[[A-Z_]+' report.md findings/ incoming/*/findings/` returns nothing
- [ ] Broad sweep: in `grep -rnF '[[' report.md findings/ incoming/*/findings/`, every hit must be real content in evidence (e.g. a bash `[[ -f x ]]` test), not a marker
- [ ] Older-style leftovers: `grep -rnE '<<|TODO|F-XXX|IR-XXX|\bXX\b|YYYY|HH:MM' report.md findings/ incoming/*/findings/` returns nothing, apart from expected hits such as a `<<EOF` heredoc inside evidence. (`\bXX\b` skips "XXE".)
- [ ] In the exported file, search (Ctrl-F) for `[[`, `XX` and `TODO`
- [ ] No future tense about testing ("we will test", "planned"). Write only about what was done.
- [ ] No reviewer comments or tracked changes left in the exported file

## 2. Navigation
- [ ] The TOC is present, and every entry jumps to the right place in the exported PDF
- [ ] Page numbers are present, with no blank pages, and each major section starts on a new page
- [ ] The Executive Summary comes directly after the TOC

## 3. Consistency
- [ ] The client name is spelled the same everywhere, and logos and branding are this client's (not a previous season's)
- [ ] The firm name is consistent throughout, with no school names or identifiers
- [ ] Dates are correct, including the year: engagement window, report date and timeline entries
- [ ] Severity counts in the Executive Summary = rows in the Findings Summary = number of findings in Section 5
- [ ] Finding IDs match across `findings-index.csv`, the summary table, the finding headings and the evidence filenames
- [ ] Every CVSS vector is version 3.1
- [ ] Every severity appears as a word, not only as a color

## 4. Content
- [ ] Every finding has numbered reproduction steps, each with the exact command or request and the expected result
- [ ] Every finding's business impact is in the client's terms, separate from the technical detail
- [ ] Every finding has a one-line "Why this severity" and at least one reference link
- [ ] Every remediation is specific (a setting, version or config) and includes a way to verify it
- [ ] Scope lists every asset class from the scope document
- [ ] The Incident and Client Interaction Log is complete
- [ ] Every row in `created-accounts-and-artifacts.csv` appears in Appendix F with its cleanup status

## 5. Evidence and redaction
- [ ] Screenshots are cropped, legible at page width, and annotated where needed
- [ ] Secrets are redacted (first and last characters only), and there are no full password hashes
- [ ] Nothing from out-of-scope systems appears anywhere
