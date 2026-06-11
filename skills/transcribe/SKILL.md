---
name: we-transcribe
description: Transcribe a parts manual PDF into an Excel-ready parts table. Handles OCR for image-based PDFs and auto-splits manuals over 100 pages. Produces the full Wave X Parts tab format ready to paste into Excel.
---

Transcribe the parts manual at `$ARGUMENTS` into the Wave X Parts tab format.

If no path is provided in `$ARGUMENTS`, ask the user: "What is the path to the parts manual PDF?"

---

## Step 1 — Analyze the PDF

Run the analysis script to check page count and detect whether the PDF is image-based:

```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/process_pdf.py --analyze "$ARGUMENTS"
```

Report back:
- Total pages
- Whether it is image-based (needs OCR) or text-based
- Whether it needs splitting (> 100 pages)

---

## Step 2 — Collect asset metadata

Before transcribing, ask the user for the following (all required):

1. **System Grouping** — the broad category (e.g., `Track Production Equipment`, `Snow Equipment`, `Trailer`)
2. **Asset Category** — the asset type in ALL CAPS (e.g., `UTILITY TRACK VEHICLE`)
3. **Manufacturer** — in ALL CAPS (e.g., `HARSCO`)
4. **Model** — the model number or name (e.g., `354AL`)
5. **Manual Name** — the name of the manual as it should appear in the "Manual Used" column (e.g., `Harsco Utility Track Vehicle-UTV 354AL Parts Manual`)

---

## Step 3 — Process the PDF (if needed)

**If image-based OR needs splitting**, run the full processing script:

```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/process_pdf.py "$ARGUMENTS"
```

This will:
- For image-based PDFs: run OCR via pytesseract and save chunks as `.txt` files
- For text-based PDFs > 100 pages: split into 100-page `.pdf` chunks
- For text-based PDFs ≤ 100 pages: use the original file directly

The script outputs a JSON result with `chunks` — a list of files with their paths and page ranges.

**If text-based and ≤ 100 pages**, skip this step. Use the original PDF directly in Step 4.

---

## Step 4 — Transcribe each chunk

For each chunk (or the full PDF if no split was needed), read and transcribe the content.

### Reading rules

**Text-based PDF chunks** — use the Read tool with the `pages` parameter in batches of up to 20 pages:
- Chunk covering pages 1–100: read pages 1–20, then 21–40, etc.
- Always read the full chunk before moving to the next one.

**OCR text file chunks** — use the Read tool to read the `.txt` file directly. The file contains page boundaries marked as `--- PAGE N ---`.

### Transcription rules (apply exactly)

- **Each page = one sub-assembly.** Extract the Sub-Assembly # and Sub-Assembly Name from the top of the page and apply them to every row on that page.
- **ALL CAPS** on all text fields.
- **No commas** anywhere in the output.
- **Leave blank** if a value is unknown — never invent or assume data.
- **Multi-line descriptions** → merge into one line (no commas).
- **If a page has no clear sub-assembly header** → ask before outputting, do not guess.
- **Identical sub-assemblies** (e.g., GEAR BOX ASSEMBLY FRONT and GEAR BOX ASSEMBLY REAR appearing on the same page) → separate rows, same sub-assembly header.
- **Build a single continuous table** — do not restart the row count between pages.

### Output columns (in order)

```
System Grouping | Asset Category | Manufacturer | Model | Sub-Assembly # | Sub-Assembly | Item # | Part | Part # | Quantity | Manual Used
```

- `System Grouping`, `Asset Category`, `Manufacturer`, `Model` — repeat the values collected in Step 2 on every row.
- `Sub-Assembly #`, `Sub-Assembly`, `Item #`, `Part`, `Part #`, `Quantity` — extracted from the manual page.
- `Manual Used` — repeat the manual name collected in Step 2 on every row.

After transcribing each chunk, confirm the page range covered and ask: "Ready for the next chunk?" before proceeding.

---

## Step 5 — Output

After all chunks are transcribed, output the complete table as a **comma-separated** block with a header row. Wrap the entire output in a code fence so it is easy to copy:

```
System Grouping,Asset Category,Manufacturer,Model,Sub-Assembly #,Sub-Assembly,Item #,Part,Part #,Quantity,Manual Used
[rows...]
```

Then tell the user:
- How many rows were produced
- How many unique sub-assemblies were found
- "Paste this into the **Wave X Parts** tab starting at column A. Then proceed with `/we-sub-assembly [wave-identifier]` to build the Sub-Assemblies and High-Level tabs."

---

## Step 6 — Write to Excel

Save the CSV and write it into the wave's Excel workbook.

1. Write the full CSV (header + all data rows) to `/tmp/we-[WAVE]-parts.csv`, replacing `[WAVE]` with the wave identifier from Step 2.
2. Run:
```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/write_tab.py \
  --file ~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx \
  --tab "Parts" \
  --csv /tmp/we-[WAVE]-parts.csv
```
3. Report the result: "Written to `~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx` → **Parts** tab ([N] rows). Proceed with `/we-sub-assembly [WAVE]` to build the Sub-Assemblies and High-Level tabs."

If `write_tab.py` returns an error about openpyxl not installed, tell the user to run: `pip3 install openpyxl`

---

## Error handling

- **Script not found**: Check that setup.sh was run. Path should be `~/Documents/projects/work-equipment-sop/scripts/process_pdf.py`.
- **PDF not found**: Report the path and ask the user to verify it.
- **OCR quality issues**: If a page produces garbled output (likely a low-quality scan), flag it and ask the user to verify that section manually against the original.
- **Page with no sub-assembly header**: Stop and ask rather than guessing — accuracy is critical for Trapeze upload.
