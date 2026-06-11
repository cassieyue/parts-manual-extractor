---
name: we-symptoms
description: Build the Wave X Symptoms tab from a service manual troubleshooting section. Classifies and groups symptoms, generates Symptom IDs in WE-AAAAAA-0000 format, enforces 30/50 character limits on Name and Description, and produces the complete Symptoms table with character-count helper columns ready for Trapeze upload.
---

Build the Symptoms tab for this wave.

`$ARGUMENTS` should be the **wave identifier** (3 letters, e.g., `WER`). If not provided, ask: "What is the 3-letter wave identifier for this wave?"

---

## Step 1 — Collect input data

Ask the user to provide the symptoms source. They can either:
- **Paste the raw symptom list** — one symptom per line, as extracted from the troubleshooting section of the service manual
- **Provide a file path** to a CSV or text file

Also ask:
- **Which assets are in this wave?** List the Asset Category, Manufacturer, and Model for each asset that needs symptoms (can be multiple assets)
- **Has this wave's Symptom ID numbering already started?** If symptoms were generated in a prior session, ask for the last Symptom ID used so the counter can continue correctly. If this is the start of the wave, the counter begins at 0005.

---

## Step 2 — Classify symptoms by category

For each asset's symptom list:
1. Assign each symptom to a broad **Symptoms Category** (e.g., ENGINE, HYDRAULIC SYSTEM, ELECTRICAL, DRIVETRAIN, COOLING SYSTEM, FUEL SYSTEM, LUBRICATION, AIR SYSTEM, BRAKES, TRANSMISSION)
2. If the service manual already provides a Symptoms/Problem category column — use it directly
3. If not — use logical judgment based on the symptom description; suggest categories to the user before finalizing

---

## Step 3 — Group similar symptoms

Within each asset, group symptoms that are closely related:
- Identical or near-identical symptom names → same group
- Variants of the same failure (e.g., "OIL LEAKS AT ACCUMULATOR" and "OIL LEAKS FROM CHISEL") → can share the same Symptom ID with different Symptom Descriptions
- A symptom may be split into two rows if splitting improves clarity
- Goal: the most concise list possible while maintaining diagnostic accuracy

Present the proposed groupings to the user and confirm before assigning IDs.

---

## Step 4 — Generate Symptom IDs

### ID format: `WE-[AAAAAA]-[NNNN]`

- `WE` — fixed prefix for all Work Equipment symptoms across all waves
- `[AAAAAA]` — 6-letter alphabetic asset identifier. Unique per asset. Generate a clear abbreviation from the asset name (e.g., UTILITY TRACK VEHICLE → UTLTKV, PTT TIE TAMPER → PTTTPR)
- `[NNNN]` — 4-digit numeric. **Starts at 0005 for each new asset and increments by 5** (0005, 0010, 0015...). Symptoms with identical names within the same asset share the same Symptom ID.

### Counter rules
- The numeric counter **resets to 0005 for each new asset** — it does not carry across assets
- If the user provided a starting counter (Step 1), begin there instead of 0005

### Character limit enforcement
- **Symptom NAME**: max **30 characters** — abbreviate if over limit
- **Symptom DESCRIPTION**: max **50 characters** — abbreviate if over limit
- If you cannot get a name under 30 characters while keeping it meaningful, flag it clearly

After generating, count characters for every Name and Description and flag any violations before outputting.

---

## Step 5 — Output

Produce the complete **Wave X Symptoms** table in a code fence.

Columns (matching Wave 8 format exactly):
```
System Grouping, Asset Category, Manufacturer, Model, Symptoms, Symptom ID (20 CHAR), Symptom NAME (30 CHAR), Symptom Description (50 CHAR), [blank], count 30, count 50
```

Notes:
- `count 30` = character count of the Symptom NAME field (helper column, matches Wave 8)
- `count 50` = character count of the Symptom DESCRIPTION field (helper column)
- Column I is blank (matches Wave 8 format)
- Sort by: Asset Category → Symptoms Category → Symptom ID

After outputting, report:
- Total symptom rows per asset
- Any Name or Description fields that are at or near the character limit (≥ 28 chars for Name, ≥ 47 chars for Description) — flag these for user review

---

## Step 6 — Write to Excel

Save the CSV and write it into the wave's Excel workbook. Use the wave identifier from `$ARGUMENTS` in place of `[WAVE]`.

1. Write the full Symptoms CSV (header + all data rows) to `/tmp/we-[WAVE]-symptoms.csv`
2. Run:
```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/write_tab.py \
  --file ~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx \
  --tab "Symptoms" \
  --csv /tmp/we-[WAVE]-symptoms.csv
```
3. Report: "Written to `~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx` → **Symptoms** tab ([N] rows)."

After all three skills have run, `~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx` will contain all four tabs — **Parts**, **Sub-Assemblies**, **High-Level**, and **Symptoms** — ready to open in Excel.

If `write_tab.py` returns an error about openpyxl not installed, tell the user to run: `pip3 install openpyxl`
