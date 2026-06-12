---
name: we-transcribe
description: Transcribe a parts manual PDF into an Excel-ready parts table. Uses parallel subagents for large manuals (> 30 pages) and single-pass for small ones. Produces the full Wave X Parts tab.
---

Transcribe the parts manual at `$ARGUMENTS` into the Wave X Parts tab format.

If no path is provided in `$ARGUMENTS`, ask the user: "What is the path to the parts manual PDF?"

---

## Step 1 — Analyze the PDF

Run the analysis script:

```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/process_pdf.py --analyze "$ARGUMENTS"
```

Report: total pages, image-based or text-based, which pipeline will be used.

---

## Step 2 — Collect asset metadata

Ask the user for all five fields before proceeding:

1. **Wave Identifier** — 3-letter code (e.g., `WER`)
2. **Asset Category** — ALL CAPS (e.g., `UTILITY TRACK VEHICLE`)
3. **Manufacturer** — ALL CAPS (e.g., `HARSCO`)
4. **Model** — (e.g., `354AL`)
5. **Manual Name** — as it appears in the "Manual Used" column

---

## Step 3 — Determine extraction strategy

- **≤ 30 pages** → single-pass (Step 4a)
- **> 30 pages** → parallel subagents (Step 4b)

---

## Step 4a — Single-pass extraction (≤ 30 pages)

Read the entire PDF using the Read tool (use `pages="1-N"` with the full page count). Apply the transcription rules below and build the full row list. Proceed directly to Step 5.

**Transcription rules:**
- Skip diagram pages, cover, TOC, legend pages — output no rows for those
- Each parts-table page has a Sub-Assembly # and Name in the header — apply to every row on that page
- Continuation pages with no header: carry the sub-assembly from the previous page
- Two-column layout: extract ALL items from BOTH columns
- ALL CAPS on all text fields; NO commas anywhere; leave blank if unknown
- Multi-line descriptions → merge into one line
- Sub-rows sharing one item number: output each as a separate row, same item number

---

## Step 4b — Parallel subagent extraction (> 30 pages)

Compute sections: split total pages into groups of 20 pages each.

Example for 189 pages → 10 sections: 1–20, 21–40, 41–60, 61–80, 81–100, 101–120, 121–140, 141–160, 161–180, 181–189.

**Launch all agents in a single message** so they run concurrently. For each section, use the Agent tool with the prompt below, substituting FIRST_PAGE, LAST_PAGE, and PDF_PATH with the actual values.

### Subagent prompt

```
You are a parts-manual extraction agent. Read pages FIRST_PAGE through LAST_PAGE of this PDF and extract all parts table rows.

PDF path: PDF_PATH

Use the Read tool with pages="FIRST_PAGE-LAST_PAGE". If the range is more than 20 pages, make two Read calls (e.g. pages="FIRST_PAGE-MID" then pages="MID+1-LAST_PAGE").

TRANSCRIPTION RULES:
- Skip diagram pages, cover pages, TOC, legend pages — no rows for those
- Each parts-table page has a Sub-Assembly # and Name in the header — apply to every row on that page
- Continuation page with no sub-assembly header: leave subassembly_num and subassembly as "" — the caller will fill them
- Two-column layout: extract ALL items from BOTH columns (left first, then right)
- ALL CAPS on all text fields; NO commas in any field; leave blank ("") if value is unknown
- Multi-line descriptions: merge into one line, no commas
- Sub-rows sharing one item number: one row per part, same item_num on each

OUTPUT:
Return ONLY a raw JSON object — no explanation, no markdown, no code fences. Any non-JSON text will break parsing.

{
  "rows": [
    {
      "subassembly_num": "D6077WAA",
      "subassembly": "DRIVE TRAIN ASSEMBLY",
      "item_num": "1",
      "part": "TRANSMISSION CLARK",
      "part_num": "0-3523010-0-08",
      "quantity": "1",
      "page_num": "7"
    }
  ],
  "last_subassembly_num": "D6077WAA",
  "last_subassembly": "DRIVE TRAIN ASSEMBLY"
}

- rows: all extracted rows in page order; empty array if no parts pages found
- last_subassembly_num / last_subassembly: the sub-assembly active on the last page of your range; empty string if no parts pages found
```

### Assembly (after all agents complete)

1. Sort agent results by section order (section 1 first).
2. **Sub-assembly carry**: walk all rows in order. When a row has empty `subassembly_num` and `subassembly`, fill them with the last non-empty values seen. When starting a new section, seed carry state with that section's `last_subassembly_num` / `last_subassembly` before processing its rows.
3. Log rows per section and note any sections that returned 0 rows (expected for all-diagram sections).

---

## Step 5 — Write CSV and report

Build the output table with these columns:

```
Asset Category,Manufacturer,Model,Sub-Assembly #,Sub-Assembly,Item #,Part,Part #,Quantity,Manual Used
```

- `Asset Category`, `Manufacturer`, `Model`, `Manual Used` — from Step 2 metadata, repeated on every row
- All other columns — from extracted rows

Write to `/tmp/we-[WAVE]-parts.csv`.

Report:
- Total rows extracted
- Unique sub-assemblies found
- Number of sections / pages skipped (diagram/non-data)

---

## Step 6 — Write to Excel

```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/write_tab.py \
  --file ~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx \
  --tab "Parts" \
  --csv /tmp/we-[WAVE]-parts.csv
```

Report: "Written to `~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx` → **Parts** tab ([N] rows). Proceed with `/we-sub-assembly [WAVE]` to build the Sub-Assemblies and High-Level tabs."

If `write_tab.py` errors on openpyxl: `pip3 install openpyxl`.

---

## Error handling

- **PDF not found**: report path, ask user to verify
- **Subagent returns malformed or non-JSON response**: try to extract JSON from the response by stripping markdown fences; if still unparseable, log section as 0 rows and note it in the final report for manual review
- **Continuation page with no prior sub-assembly context** (first section of manual starts mid-table): flag those rows in the report — do not guess
- **Diagram-heavy sections returning 0 rows**: expected; log and continue
