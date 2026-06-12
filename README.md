# Parts Manual Extractor

A Claude Code plugin that extracts structured parts data from scanned equipment manuals (image-only PDFs) and writes the results directly to Excel.

Reduces manual data entry from **2–4 hours per 100 pages to ~15 minutes of review**.

---

## What it does

Equipment maintenance teams receive parts manuals as scanned PDFs. Every part — item number, description, part number, quantity — must be entered into a maintenance management system. This plugin automates that extraction.

Given a PDF, it:
1. Reads the manual visually, handling two-column layouts and diagram pages automatically
2. Extracts all parts rows into a structured ten-column schema
3. Generates sub-assembly breakdowns and repair task IDs
4. Writes everything to a formatted Excel workbook ready for upload

For manuals over 30 pages, it splits into parallel sections and reads them simultaneously — a 189-page manual completes in ~4 minutes.

---

## Skills

| Command | What it does |
|---|---|
| `/we-transcribe <pdf>` | Extract all parts rows from a manual → Parts tab |
| `/we-sub-assembly <wave>` | Generate sub-assembly list and repair task IDs → Sub-Assemblies + High-Level tabs |
| `/we-symptoms <wave>` | Classify symptoms per sub-assembly → Symptoms tab |

---

## Setup

```bash
./setup.sh
```

Then install the plugin in Claude Code:

```
/plugins install .
```

---

## Output

Each wave produces an Excel workbook (`output/<WAVE>.xlsx`) with three tabs:

- **Parts** — every part row extracted from the manual (asset, manufacturer, model, sub-assembly, item #, part, part #, quantity)
- **Sub-Assemblies** — deduplicated sub-assembly list with repair task IDs
- **High-Level** — functional groupings for assets with 50+ sub-assemblies

---

## Validation

Tested against the Harsco Utility Track Vehicle 354AL Parts Manual (189 pages):
- **1,736 parts rows** extracted
- **55 sub-assemblies** identified
- **100% row capture** on controlled 14-page validation test

---

## Tech

- Claude Code plugin (skills / slash commands)
- Python scripts for PDF analysis and Excel writing
- Uses Claude's native PDF reading — no OCR preprocessing required
