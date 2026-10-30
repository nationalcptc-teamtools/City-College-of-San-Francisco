*Draft: command steps not filled in yet.*

# 1. Access and Identity Data: Badges, Barcodes, QR Codes

- **Phase:** Any: shows up on any host, share or web app, not one lane
- **Risk:** 🟢 Safe *(proposed)*: reading files and decoding codes. **Making or using a copied badge, pass or ticket is 🔴 Risky:** ask the client contact in writing first, every time.
- **Tier:** Recognize *(proposed)*
- **Finding:** none in the library yet
- **Tools:** a file share browser (or the share-listing tools in the Windows playbooks), a barcode / QR reader, a base64 decoder
- **You need:** access to the share, host or app where the files sit

## What it is
Data that opens doors or proves identity often sits where anyone can read it:

1. **RFID/NFC badge files on open shares:** badge-printing exports, card-number lists, or saved card dumps from badge readers. A card number plus the format is often enough to clone a badge.
2. **Barcodes** on passes and tickets that carry personal data, not just a lookup number.
3. **QR codes** on tickets and passes: they often hold a readable link, an ID or a token (decode it; see Web #06 for base64 and JWTs inside).

**The 2024 example** (credit: the 2024 team; an airport scenario): the barcode on a printed boarding pass held the customer's name and national ID number. The web app's page source showed what each field meant, so anyone who scanned a pass could read them.

Report what the data lets someone do (enter a building, board, impersonate), not just that it exists.

**Fix to recommend:** keep personal data out of codes and badges (use a lookup ID checked on the server); restrict shares holding badge data; sign or expire tokens in QR codes.

## Commands
[[TODO: Write the steps. For barcodes, copy from the 2024 doc "Web - Expose Personally Identifiable Information.docx" (leave out the 2024 hosts, IPs, URLs, company names and screenshots). For badge files and QR codes there's no 2024 doc. Format per `templates/finding.md`: numbered steps, exact command in backticks, an "Expected:" line under each.]]

## Evidence to capture
- `evidence/F-NNN-01.png`: where the file or code was found (share path or page), with the host visible.
- `evidence/F-NNN-02.png`: the decoded contents, personal data and card numbers redacted to the first and last characters.

## Practice
- [[TODO: none in the 2024 doc; any barcode or QR code the team generates itself]]

---
*Adapted from the CCSF 2024 Web playbooks. Updated by the CCSF 2026 team.*
