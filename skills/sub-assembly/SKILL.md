---
name: we-sub-assembly
description: Build the Wave X Sub-Assemblies and Wave X High-Level tabs from the Parts tab data. Deduplicates sub-assemblies, creates high-level groupings for assets with 50+ sub-assemblies, generates unique 3-letter asset identifiers, and produces Repair Task IDs in AAA-AAA-0000 format ready for Trapeze upload.
---

Build the Sub-Assemblies and High-Level tabs for this wave.

Before starting, ask the user: **"What is the 3-letter wave identifier for this wave?"** — do not assume a value even if one was passed in `$ARGUMENTS`. Confirm it before proceeding.

---

## Step 1 — Collect input data

Ask the user to provide the parts data. They can either:
- **Paste CSV rows** directly from the Wave X Parts tab (header + data rows), or
- **Provide a file path** to the Wave X Parts CSV

The expected columns are:
```
Asset Category, Manufacturer, Model, Sub-Assembly #, Sub-Assembly, Item #, Part, Part #, Quantity, Manual Used
```

Only columns A–E are needed for this workflow (Asset Category through Sub-Assembly). Confirm receipt before proceeding.

---

## Step 2 — Deduplicate sub-assemblies

From the input data:
1. Extract only the columns: **Asset Category, Manufacturer, Model, Sub-Assembly #, Sub-Assembly**
2. Remove duplicate rows (same Sub-Assembly # + Asset Category = duplicate)
3. Sort by: Asset Category → Sub-Assembly #

Report how many unique sub-assemblies were found per asset category.

---

## Step 3 — Count and flag large assets

For each asset category, count the number of unique sub-assemblies.

**If any asset has 50 or more sub-assemblies** → that asset requires a High-Level Breakdown (see Step 4).

Report the count per asset:
```
UTILITY TRACK VEHICLE (HARSCO 354AL): 87 sub-assemblies → requires High-Level Breakdown
RAILCAR MOVER (SHUTTLEWAGON SWX35-A): 52 sub-assemblies → requires High-Level Breakdown
UTILITY TRAILER (SUNDOWN TRAILER UNKNOWN): 3 sub-assemblies → no High-Level needed
```

---

## Step 4 — High-Level Breakdown (assets with 50+ sub-assemblies only)

For each large asset, create high-level groups that logically organize all its sub-assemblies.

### Grouping guidance
- Group sub-assemblies by functional similarity (e.g., all engine-related assemblies → ENGINE AND RELATED COMPONENTS)
- The parts manual's table of contents is the best starting point — use it if available
- Aim for 6–12 groups per large asset; avoid groups with only 1–2 sub-assemblies unless unavoidable
- Groups must only contain sub-assemblies from the same asset category
- Suggest group names in ALL CAPS

### High-Level Codes
- Codes start at **1000** and increment by **10** for each group
- Codes are **sequential across all assets in the wave** — do not reset when moving to a new asset
- Example: Asset A gets 1000–1070, Asset B continues from 1080, etc.

### 3-letter codes for each high-level group
- Suggest a clear 3-letter abbreviation for each group (e.g., VCH for Vehicle Chassis, ENG for Engine)
- Codes must be **unique across all groups in the entire wave** (including groups from non-high-level assets)
- Present the groupings table to the user and ask for confirmation:

```
High-Level Code | Sub-Assembly (Grouped)        | 3-letter Code
1000            | VEHICLE CHASSIS AND DRIVE TRAIN | VCH
1010            | ENGINE AND RELATED COMPONENTS   | ENG
1020            | CAB AND BODY COMPONENTS         | CAB
...
```

**Do not finalize groupings without user confirmation.** The SOP requires supervisor review before proceeding.

---

## Step 5 — Build the High-Level tab

For assets that had a High-Level Breakdown, produce the **Wave X High-Level** table:

Columns:
```
Asset Category, Manufacturer, Model, High Level Code, Sub-Assembly (Grouped), [blank], [3-letter code]
```

Note: the last two columns match the Wave 8 pattern — the second-to-last column is blank, the last column is the 3-letter code.

Output as a comma-separated table in a code fence.

---

## Step 6 — Assign codes for non-high-level assets

For each asset with **fewer than 50 sub-assemblies**, assign a single 3-letter code that clearly represents the asset category name.

- Must be unique across all codes in this wave (including high-level group codes assigned in Step 4)
- Example: UTILITY TRAILER → UTT

Present to the user and confirm before proceeding.

---

## Step 7 — Generate Repair Task IDs

For each row in the deduplicated sub-assemblies list, assign a Repair Task ID and Repair Task Description.

### ID format: `[WAVE]-[ASSET/GROUP]-[NNNN]`

- `[WAVE]` = the wave identifier from `$ARGUMENTS` (e.g., `WER`)
- `[ASSET/GROUP]` = 3-letter code for the high-level group (if asset has High-Level) OR the asset's 3-letter code (if no High-Level)
- `[NNNN]` = 4-digit numeric, **starts at 0010, increments by 10**, **resets to 0010 each time the asset/group code changes**

### Header sub-assemblies (no numeric segment)
When the first sub-assembly in a group shares the same name as the group itself (e.g., CAB ASSEMBLY within the CAB group), it is the header entry. Its Repair Task ID omits the numeric segment (e.g., `WER-CAB` not `WER-CAB-0010`).

### Grouping similar sub-assemblies
- Two sub-assemblies may share the same Repair Task ID if they have nearly identical names or are closely related functional variants (e.g., GEAR BOX ASSEMBLY FRONT and GEAR BOX ASSEMBLY REAR → both `WER-VCH-0050` with Repair Task Description `GEAR BOX`)
- Repair Task Descriptions should be concise — shorten where reasonable

### Verification
After generating all IDs, verify that:
1. All 3-letter codes are unique within this wave
2. Numeric segments reset correctly at each code boundary
3. No two different groups share the same 3-letter code

---

## Step 8 — Output

Produce two tables in code fences:

### Table 1: Wave X Sub-Assemblies tab
Columns:
```
Asset Category, Manufacturer, Model, High Level Code, Sub-Assembly #, Sub-Assembly, Repair Task ID, Repair Task Description
```
- `High Level Code` — the numeric code (e.g., 1000) for assets with High-Level grouping; **blank** for assets without
- All other fields from deduplication + generated IDs

### Table 2: Wave X High-Level tab
(Only output if any assets had a High-Level Breakdown — otherwise state "No High-Level tab needed for this wave.")

Columns: as defined in Step 5.

Then tell the user:
- Total rows in Sub-Assemblies tab
- Number of assets that required a High-Level Breakdown
- "When groupings are confirmed with the project supervisor, proceed to `/we-symptoms [wave-identifier]` for the Symptoms tab."

---

## Step 9 — Write to Excel

Save each table and write both tabs into the wave's Excel workbook. Use the wave identifier from `$ARGUMENTS` in place of `[WAVE]`.

**Sub-Assemblies tab:**
1. Write the Sub-Assemblies CSV to `/tmp/we-[WAVE]-sub-assemblies.csv`
2. Run:
```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/write_tab.py \
  --file ~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx \
  --tab "Sub-Assemblies" \
  --csv /tmp/we-[WAVE]-sub-assemblies.csv
```

**High-Level tab (only if a High-Level Breakdown was produced):**
1. Write the High-Level CSV to `/tmp/we-[WAVE]-high-level.csv`
2. Run:
```bash
python3 ~/Documents/projects/work-equipment-sop/scripts/write_tab.py \
  --file ~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx \
  --tab "High-Level" \
  --csv /tmp/we-[WAVE]-high-level.csv
```

Report: "Written to `~/Documents/projects/work-equipment-sop/output/[WAVE].xlsx` → **Sub-Assemblies** tab ([N] rows)[, **High-Level** tab ([N] rows)]."

If `write_tab.py` returns an error about openpyxl not installed, tell the user to run: `pip3 install openpyxl`
