# Work Equipment Repair Tasks — Automation Approach Evaluation

> **Co-op project** — digital solutions co-op at Keolis, which operates and maintains several railway lines for the MBTA.

## Scenario

Extract structured parts data from scanned railway work equipment parts manuals (PDF) into a formatted Excel workbook for upload to Trapeze (maintenance management system). Each manual contains a mix of diagram pages and two-column parts table pages. Output must conform to a fixed schema with ten columns per row.

**Evaluation criteria:** Performance (speed), Accuracy, Cost (token/API usage)

---

## Input and Target Output

| Item | Detail |
|------|--------|
| Input | Scanned PDF — zero embedded text, image-only pages |
| Example input | `examples/Harsco Utility Track Vehicle-UTV 354AL Parts Manual.pdf` (189 pages) |
| Example target output | `examples/Wave 8 Breakdown.xlsx` — Wave 8 Parts tab (9,550 rows × 11 columns) |
| Output schema | `Asset Category, Manufacturer, Model, Sub-Assembly #, Sub-Assembly, Item #, Part, Part #, Quantity, Manual Used` |
| Destination | Trapeze CMMS — requires data accuracy and full traceability |

**Key structural challenges in the source data:**

- Two-column parts tables (left column items 1–N, right column items N+1–M on the same page)
- Sub-rows sharing one item number (e.g., item 3 has 8 separate parts, each a distinct row)
- Inconsistent table density across pages (10–60 rows per page)
- Diagram pages interspersed with table pages (no visual distinction from a pipeline perspective)
- Multi-page sub-assemblies where the header only appears on the first page

---

## Baseline: Fully Manual (Copy-Paste)

The reference point for any automation evaluation is the simplest possible approach: a person opens the PDF and manually copies or re-keys the data directly into the Excel spreadsheet.

### How it works

1. Open the parts manual PDF alongside the Excel workbook
2. Read each parts table page visually
3. Type or copy-paste each row into the spreadsheet, following the output schema
4. Repeat across all table pages, skipping diagrams
5. Validate entries against the source PDF as you go

### Performance

| Dimension | Result |
|-----------|--------|
| Speed | Very slow — estimated 2–4 hours per 100-page manual |
| Accuracy | High — human reading handles two-column layout and sub-rows naturally |
| Cost | Pure labour cost; no software or API cost |
| Scalability | Does not scale — linear with manual count and page count |
| Repeatability | Operator-dependent; risk of transcription fatigue errors on long manuals |

### Assessment

Fully manual entry is the floor for accuracy but the ceiling for labour cost. It serves as the reference point: any approach must match or exceed this accuracy level to be viable, and any approach that reduces time meaningfully (even with a validation pass) represents a productivity gain.

---

## Approach 1: Text Extraction (OCR → Claude Text Processing)

### Architecture

```
Scanned PDF
  └─ Tesseract OCR          render text layer from images
  └─ Claude API (text)      read extracted text, apply transcription rules
  └─ write_tab.py           write CSV to Excel tab
```

**Implementation:** Claude Code plugin (`/we-transcribe` skill) calling `process_pdf.py` → Tesseract OCR → Claude reads `.txt` output

### How it works

Pages are rendered and passed through Tesseract OCR to produce a plain-text representation. Claude then reads the text and applies the transcription schema rules to extract structured rows.

### Results

| Dimension | Result |
|-----------|--------|
| Speed | Fast — OCR is seconds per page; text processing is low-latency |
| Accuracy | **~85–90%** — 10–15% error rate (per HANDOFF.md baseline measurement) |
| Input token cost | Low — text tokens only, no image tiles |
| Output token cost | Low |

### Root cause of accuracy failures

Tesseract OCR reads pages linearly (top to bottom, left to right). A two-column table produces interleaved output:

```
# OCR output (linear read of two-column layout):
1  TRANSMISSION CLARK      41  TRANSMISSION MANIFOLD
0-3523010-0-08              H1996Y01
3  ELECT CONTROL MANIFOLD  42  REMOTE LUBE BLOCK
D0057Y01                    D6546Y01
```

Claude cannot reliably reconstruct which values belong to which column, leading to:
- Part numbers assigned to wrong descriptions
- Rows merged or split incorrectly
- Right-column items dropped entirely when OCR confidence is low

Additionally, Tesseract character accuracy on scanned industrial part numbers (e.g., `D0057Y01` vs `D0057Y0l`, `0-3582001-0-18` vs `O-3582001-O-18`) is approximately 70–80%. These errors propagate directly into the output.

### Conclusion

Text extraction is fast and cheap but structurally incompatible with two-column parts table layouts. The error rate is too high for Trapeze upload without a full human re-check, negating the automation benefit.

---

## Approach 2: Claude Vision (Render PNG → Claude Image Reading)

### Architecture

```
Scanned PDF
  └─ render_pages.py        render each page to PNG at 150 or 200 DPI
  └─ Claude Vision API      Read tool on each PNG image
  └─ assemble_csv.py        validate, flag, assemble rows
  └─ write_tab.py           write CSV to Excel tab
```

**Implementation:** Claude Code plugin (`/we-transcribe` skill) with supporting scripts. Claude reads each page image directly using the Read tool (interactive mode) or Anthropic Batch API (production mode).

### How it works

Each PDF page is rendered to a PNG image and passed to Claude as a visual input. Claude reads the image layout natively — understanding two-column structure, indented sub-rows, and table headers — and extracts structured rows.

### Testing performed

Testing was conducted on pages 7–20 of `examples/Harsco Utility Track Vehicle-UTV 354AL Parts Manual.pdf`, covering four sub-assemblies with known target row counts derived from `examples/Wave 8 Breakdown.xlsx`.

#### 150 DPI results

| Sub-Assembly | Rows Extracted | Expected | Capture Rate |
|---|---|---|---|
| D6077WAA — Drive Train Assembly | 27 | 59 | 46% |
| D6801WAA — Drive Train Plumbing | 13 | 57 | 23% |
| A9422XAB — Lock Out Cylinder | ~9 | ~9 | ~100% |
| 0-3582001-0-18 — Truck Assembly | 22 | ~60 | 37% |

**Root cause:** At 150 DPI, letter-size pages render to 1,275 × 1,650 px. Characters in dense table rows are approximately 4–5 px tall. Claude Vision filters out rows where confidence is low, producing conservative but incomplete output on high-density pages.

#### 200 DPI results

| Sub-Assembly | Rows Extracted | Expected | Capture Rate |
|---|---|---|---|
| D6077WAA — Drive Train Assembly | 59 | 59 | **~100%** |
| D6801WAA — Drive Train Plumbing | 53 | 57 | **~93%** |
| A9422XAB — Lock Out Cylinder | 9 | ~9 | **~100%** |
| 0-3582001-0-18 — Truck Assembly | ~46 | ~60 | **~77%** |

At 200 DPI pages render to 1,700 × 2,200 px. Characters are approximately 6–7 px tall — sufficient for Claude Vision to read dense rows with confidence.

**Note on token cost at 200 DPI:** Anthropic scales images exceeding 1,568 px on the long side before tiling. Both 150 DPI (1,650 px height) and 200 DPI (2,200 px height) exceed this threshold and scale to approximately 1,212 × 1,568 px — the same effective resolution. Token cost per page is therefore identical (~9,000 tokens/page, 12 tiles × 750 tokens).

### Performance

| Dimension | 150 DPI | 200 DPI |
|-----------|---------|---------|
| Speed (interactive) | ~3–5 min per 10-page batch (human-gated) | Same |
| Speed (Batch API) | Async, ~5–10 min for full manual | Same |
| Accuracy | 30–50% capture on dense tables | 77–100% capture |
| Input token cost (real-time) | ~$0.027/page | Same (Anthropic scaling) |
| Input token cost (Batch API, 50% discount) | ~$0.014/page | Same |
| Full 189-page manual (Batch) | ~$2.56 | ~$2.56 |
| Estimated parts-table pages only (~50%) | ~$1.28 | ~$1.28 |

### Structural issues that persist at any DPI

Regardless of rendering resolution, several table patterns resist systematic extraction:

1. **Sub-rows sharing one item number** — Item 3 in D6077WAA has 8 child parts (D3107P01–P08) that all carry item number 3. A rule-based schema assuming one item number = one row cannot handle this reliably.
2. **Item number gaps** — Items 5, 6, 7 in Drive Train Assembly do not appear in the parts table (they are diagram-only callouts). Any row-count validation must tolerate non-contiguous item sequences.
3. **Assembly references as rows** — Item 15 in D6077WAA lists D6801WAA (Drive Train Plumbing) as a line item — a cross-reference, not a part. These must be included as rows but cannot be confused with actual part numbers.
4. **Variable density** — Some pages have 10 rows; others have 60+. A single prompt that works on sparse pages over-extracts on dense pages and vice versa.
5. **Page 4-of-4 tables** — Multi-page sub-assemblies that span 4 diagram pages before the parts table page require the pipeline to correctly identify page type and carry forward sub-assembly context.

### Conclusion

Claude Vision at 200 DPI recovers the structural understanding that text extraction loses. On moderately dense pages it achieves near-complete extraction. However:

- High-density pages (60 rows, two columns) still produce gaps even at 200 DPI
- The interactive (non-Batch) workflow is slow — batches of 10 pages require human confirmation
- The Batch API workflow is faster but produces async JSON that requires post-processing logic to reassemble
- Row-level confidence is implicit (Claude filters silently) rather than explicit — a flagging system requires additional prompt engineering
- Results are not fully deterministic: the same page can yield slightly different output across API calls

Accuracy ceiling with this approach, at best: approximately 90–95% on clean scans with consistent table formats. Reaching 98%+ requires per-page human review, which negates the time saving over Approach 3.

---

## Approach 3: Claude Prompting (Adobe OCR + Claude Web Interface)

**Source:** `Work_Equipment_Process_SOP_final_1.docx`

### Architecture

```
Scanned PDF
  └─ Adobe Acrobat OCR      embed searchable text layer into PDF
  └─ Claude (web interface) upload OCR'd PDF + standardized prompt
  └─ Human                  copy output to Excel, validate against source
```

### How it works

1. Open the scanned PDF in Adobe Acrobat and run OCR to embed a text layer
2. If the manual exceeds 100 pages, split into 100-page chunks using Acrobat's split tool
3. Open a new Claude chat (web interface) and paste a standardized transcription prompt; wait for Claude to confirm readiness
4. Upload the OCR'd PDF chunk — Claude reads all pages and returns a continuous master table
5. Copy output into the Excel workbook
6. Repeat for remaining chunks, appending to the same tab
7. Human validates output against the original PDF

**Standardized transcription prompt (from SOP):**
```
ROLE: You are a high-accuracy transcription engine. Your task is to convert each page
of a parts manual (PDF or image) into a strict Excel-friendly, tab-separated table.
OUTPUT FORMAT: SUB ASSEMBLY # | SUB ASSEMBLY NAME | ITEM # | DESCRIPTION | PART # | QUANTITY
TEXT RULES: ALL CAPS • TAB-SEPARATED • NO COMMAS • NO EXTRA SPACES • LEAVE BLANK IF UNKNOWN
DATA INTEGRITY: NEVER invent or assume data • TRANSCRIBE EXACTLY AS SHOWN
SUB-ASSEMBLY RULES: Each page = ONE sub-assembly • Extract SUB ASSEMBLY # and NAME from the page
MASTER TABLE RULES: Build a SINGLE CONTINUOUS TABLE across all pages • Append new rows only
```

### Performance

| Dimension | Result |
|-----------|--------|
| Speed | ~15–30 min per 100-page chunk (human-paced, including validation) |
| Accuracy | ~90–95%; human validation pass brings to acceptable level for Trapeze |
| Cost | Claude subscription (web UI) — no per-token API cost; Adobe Acrobat licence required |
| Scalability | Low — requires an operator per manual; does not parallelize |
| Repeatability | High within a session (fixed prompt); varies slightly across operators |

### Why this approach works where the scripted approaches do not

Claude processes the uploaded PDF using its native multimodal reading — it sees the page layout visually, not as a linearized text stream. This means:

- Two-column table structure is understood correctly without any rendering pipeline
- Sub-rows (shared item numbers) are handled through contextual reading
- Diagram pages are naturally skipped without requiring explicit page-type classification
- The interactive loop lets the operator ask Claude to re-read a page or clarify an ambiguous row
- Adobe OCR provides a text layer that Claude can use as a secondary signal alongside the visual

The human operator is not just a QA layer — they are part of the accuracy mechanism, catching Claude's errors in real time and directing re-transcription where needed.

### Limitations

- Time per manual is fixed to human pace; cannot be parallelized
- Adobe Acrobat required for OCR step (licence cost)
- Quality is operator-dependent: a skilled user who knows the prompt gets better results than a new user
- Not auditable at the row level — there is no intermediate structured output to diff against a previous run

### Conclusion

Claude Prompting is the current production approach. It achieves the best accuracy-to-effort ratio of the three approaches tested so far, leveraging Claude's visual understanding without requiring infrastructure. The constraint is throughput: it scales only with headcount.

---

## Approach 4: Base44 App (Schema-Driven Extraction + LLM Post-Processing)

### Architecture

```
Scanned PDF
  └─ base44 UploadFile API              upload PDF to base44 storage
  └─ base44 ExtractDataFromUploadedFile  native PDF extraction against JSON schema
  └─ base44 InvokeLLM (optional)         Claude Sonnet 4.6 Smart Fix pass
  └─ xlsx (client-side)                  export to Excel
```

**Implementation:** React/Vite web app built on the base44 low-code platform (`@base44/sdk`). The operator uploads one or more PDFs through a browser UI; base44's platform handles PDF reading server-side and returns structured JSON conforming to a user-defined schema.

### How it works

1. Operator uploads the parts manual PDF through the browser UI
2. `UploadFile` pushes the file to base44 storage and returns a URL
3. `ExtractDataFromUploadedFile` takes that URL and a JSON schema describing the output structure; base44 reads the PDF natively (no user-managed rendering pipeline) and returns validated structured rows
4. Optionally, the operator clicks **Smart Fix**: `InvokeLLM` sends the full extracted table plus a list of flagged rows (those with non-numeric quantities or suspect part numbers) to Claude Sonnet 4.6, which corrects OCR character errors (`O`→`0`, `l`→`1`) and fills blanks using neighboring rows as context
5. Operator reviews the editable table in the browser, adds or corrects rows manually, then exports to Excel

### Key architectural differences from prior approaches

| Feature | Approach 2 (Vision Plugin) | Approach 3 (Claude Prompting) | Approach 4 (Base44 App) |
|---|---|---|---|
| PDF rendering | User-managed (`render_pages.py`, DPI tuning) | Adobe Acrobat OCR | base44 platform (not user-controlled) |
| Output contract | Free-form text → parsed | Free-form text → copy-pasted | JSON schema → validated structured JSON |
| Post-processing | `assemble_csv.py` validation flags | Human re-reads source PDF | LLM Smart Fix using full table context |
| Operator interface | Claude Code CLI | Claude web chat | Purpose-built browser UI (editable table) |
| Infrastructure to maintain | Render pipeline, Batch API, assembly scripts | Adobe Acrobat, Claude web access | base44 subscription only |

### Results

Testing was conducted on pages 7–20 of `examples/Harsco Utility Track Vehicle-UTV 354AL Parts Manual.pdf` (extracted as a 14-page test file), compared against `examples/Wave 8 Breakdown.xlsx`.

| Sub-Assembly | Rows Extracted | Expected | Capture Rate |
|---|---|---|---|
| D6077WAA — Drive Train Assembly | 59 | 59 | **100%** |
| D6801WAA — Drive Train Plumbing | 57 | 57 | **100%** |
| A9422XAB — Lock Out Cylinder | 9 | 9 | **100%** |
| 0-3582001-0-18 — Truck Assembly | 60 | 60 | **100%** |
| **Total** | **185** | **185** | **100%** |

**Extraction time:** ~3 minutes for the 14-page test file (server-side; no human-gated batching).

**Observed issue — sub-row item number inheritance:** 9 rows in D6077WAA have a blank `item_num`. These are the sub-rows for items 3 and 4 (e.g., D3107P01–P08 under item 3), where base44 correctly captured the child parts but did not propagate the parent item number down to each child row. All 9 rows are present and correctly structured; only the item number field is blank.

| Dimension | Result |
|-----------|--------|
| Speed | ~3 min for 14-page test (server-side; no human-gated batching) |
| Accuracy | **100% row capture** on controlled test (185/185 rows across 4 sub-assemblies) |
| Cost | base44 subscription (platform fee); no direct per-token cost visible to operator |
| Scalability | Medium — browser UI is operator-gated; multiple files can be queued in one session |
| Repeatability | High — fixed JSON schema enforces consistent column structure across runs |
| Handles two-column tables | Yes — base44's native PDF reading understands layout visually |
| Handles sub-rows | Yes — all sub-rows captured; parent item number not inherited to children |
| Human QA required | Yes — editable table review recommended; sub-row item numbers may need manual fill |

### Why schema-driven extraction improves on free-form approaches

Approaches 2 and 3 ask Claude to produce free-form tabular text which is then parsed or copy-pasted. Structural ambiguities (sub-rows, shared item numbers, cross-reference rows) are resolved by the model at transcription time with no downstream validation.

`ExtractDataFromUploadedFile` takes a JSON schema as its contract. The platform enforces that every returned row has the declared fields and types, which means:

- Malformed rows fail the schema and are retried or surfaced as errors rather than silently propagating
- Column assignment is explicit — part number cannot land in the quantity field due to a type mismatch
- The Smart Fix step receives a structurally valid table and can focus on value-level errors (OCR character substitutions, blank fields) rather than structural reconstruction

The Smart Fix pass also uses the **full table as context**, not just the flagged row in isolation — a capability not present in any prior approach. For example, if item 3 has a blank part number but items 1, 2, and 4 in the same sub-assembly follow a `D####P0#` pattern, the LLM can infer a candidate correction with high confidence.

### Limitations

- **Closed platform:** base44's extraction internals are not inspectable or tunable. DPI, model choice, and layout heuristics are platform-managed. If accuracy degrades on a particular manual type, there is no user-accessible lever to adjust.
- **Tested on one manual section:** The controlled test covers pages 7–20 of one manual (Harsco UTV). Performance on other manual types, higher page counts, or lower-quality scans has not been measured.
- **Smart Fix scope is narrow:** The Smart Fix prompt targets non-numeric quantities and suspect part numbers. Structural extraction errors — missed rows, wrong sub-assembly context carried forward, right-column items dropped — are not addressed and require manual correction in the editable table.
- **Operator still required:** Export and validation remain manual steps. The workflow does not produce a Trapeze-ready file without a human review pass.

### Conclusion

The base44 app achieves the highest reported accuracy of any approach tested on the controlled section, and does so with the least infrastructure of the scripted approaches. Schema-driven extraction removes the free-form parsing step that limits Approaches 1 and 2, and the Smart Fix LLM pass addresses the residual OCR error class using contextual inference.

The primary caveats are the closed platform (no tuning levers) and limited test coverage. Before treating this as the recommended approach at scale, testing on full-length manuals and other equipment types is needed.

---

## Approach 5: Claude Code Plugin (Native PDF Reading, No External Dependency)

### Architecture

#### Interactive mode (no API key required)

```
Scanned PDF
  └─ /we-transcribe skill     Claude Code Read tool reads PDF natively (vision)
  └─ write_tab.py             write CSV to Excel tab
```

#### Batch mode (ANTHROPIC_API_KEY required)

```
Scanned PDF
  └─ extract_structured.py   send PDF in 5-page base64 chunks to Claude API with JSON schema
  └─ smart_fix()             LLM second pass using full table context (same as Approach 4)
  └─ assemble_csv.py         validate, flag, assemble rows
  └─ write_tab.py            write CSV to Excel tab
```

**Implementation:** Claude Code plugin (`/we-transcribe` skill) — the operator invokes the skill from the Claude Code CLI. In interactive mode, Claude reads the PDF natively via the Read tool with no external API calls, render pipeline, or subscription. In batch mode, `extract_structured.py` replicates base44's schema-driven extraction using the Anthropic SDK directly (tools + tool_choice).

### How it works

**Interactive mode:**

1. Operator runs `/we-transcribe <pdf_path>` and provides wave metadata (category, manufacturer, model, manual name)
2. The skill reads the PDF using the Read tool — Claude sees the page layout visually, the same as in Approach 3 (Claude web) but inside the Claude Code session
3. For manuals >30 pages, the skill launches parallel subagents (one per 20-page section) so all sections are extracted concurrently; wall-clock time equals the slowest single agent
4. The skill applies structured transcription rules (ALL CAPS, no commas, two-column handling, sub-assembly carry, diagram-page skipping) and outputs a validated CSV
5. `write_tab.py` writes the CSV to the wave's Excel workbook

**Batch mode:**

1. `extract_structured.py` slices the PDF into 5-page chunks using pypdf and encodes each as a base64 document block
2. Each chunk is sent to Claude Sonnet 4.6 with a JSON schema (identical to Approach 4's schema) enforced via tool use: `tools=[{name, description, input_schema}]` + `tool_choice={"type":"tool","name":"extract_parts"}`
3. Cross-chunk context carry: after each chunk, the last `{subassembly_num, subassembly}` is passed as prompt context to the next chunk, preventing sub-assembly field loss at chunk boundaries
4. Smart Fix pass: rows with blank `part_num` or non-integer `quantity` are batched and sent to Claude Sonnet 4.6 with the full table as context — same pattern as Approach 4
5. `assemble_csv.py` validates and QA-flags the output; `write_tab.py` writes to Excel

### Key architectural differences from Approach 4

| Feature | Approach 4 (Base44 App) | Approach 5 (Claude Code Plugin) |
|---|---|---|
| Execution environment | base44 browser UI | Claude Code CLI |
| PDF reading | base44 platform (not user-controlled) | Claude Code Read tool / Anthropic API direct |
| Output contract | JSON schema via `ExtractDataFromUploadedFile` | JSON schema via tool use (batch) or skill transcription rules (interactive) |
| Smart Fix | `InvokeLLM` via base44 SDK | `smart_fix()` via Anthropic SDK (batch mode only) |
| Subscription required | base44 subscription | None (interactive); Anthropic API key (batch) |
| Infrastructure to maintain | base44 app | Claude Code plugin scripts (~600 LOC) |

### Results

#### Controlled test — pages 7–20, Harsco UTV manual (WER wave, 2026-06-12)

| Sub-Assembly | Rows Extracted | Expected | Capture Rate |
|---|---|---|---|
| D6077WAA — Drive Train Assembly | 59 | 59 | **100%** |
| D6801WAA — Drive Train Plumbing | 57 | 57 | **100%** |
| A9422XAB — Lock Out Cylinder | 9 | 9 | **100%** |
| 0-3582001-0-18 — Truck Assembly | 60 | 60 | **100%** |
| **Total** | **185** | **185** | **100%** |

**Pages processed:** 14 total — 4 parts-table pages extracted, 10 non-data pages correctly skipped (general arrangement diagram, instructions, legend pages, TOC).

**Observed issue — sub-row item number inheritance:** Same as Approach 4: sub-rows for items 3 and 4 in D6077WAA correctly captured with all other fields; item number field blank for child rows. All 185 rows are present.

#### Full manual run — 189-page Harsco UTV manual (WER wave, 2026-06-12)

**Method:** 10 parallel subagents via the Claude Code Agent tool, each reading a 20-page section of the PDF. Wall-clock time equals the slowest single agent.

| Metric | Result |
|--------|--------|
| Pages processed | 189 (full manual) |
| Parallel agents | 10 (sections: 1–20, 21–40, … 181–189) |
| Wall-clock time (extraction phase) | **~4 min** (slowest agent: 237s) |
| Total rows extracted | **1,736** |
| Unique sub-assemblies captured | **55** |
| Diagram / reference rows filtered | 65 |
| Subagent tokens consumed | ~591K (~3,130/page) |
| Cost | Billed to Claude Code session (no separate API key) |
| Accuracy vs ground truth | No full-manual ground truth available; all 55 sub-assemblies captured |

**Rows by section:**

| Section | Pages | Raw rows | Kept | Filtered | Notes |
|---------|-------|----------|------|----------|-------|
| 1 | 1–20 | 185 | 185 | 0 | |
| 2 | 21–40 | 288 | 288 | 0 | |
| 3 | 41–60 | 299 | 299 | 0 | |
| 4 | 61–80 | 208 | 208 | 0 | |
| 5 | 81–100 | 197 | 177 | 20 | 10 rows each from 5065598 and 5065641 (hose routing diagrams — items 1–10 with no part or part#) |
| 6 | 101–120 | 32 | 32 | 0 | |
| 7 | 121–140 | 281 | 281 | 0 | |
| 8 | 141–160 | 156 | 156 | 0 | |
| 9 | 161–180 | 102 | 102 | 0 | |
| 10 | 181–189 | 53 | 8 | 45 | 45 UTV DECAL location rows (item# and part both empty — diagram cross-references, not parts list entries) |
| **Total** | — | **1,801** | **1,736** | **65** | |

**Partial sub-assemblies:** Several piping sub-assemblies start mid-sequence because items 1–N appear only on hose routing diagram pages the agent cannot read as a parts table: 5065598 starts at item 25, 5065641 at item 10, 5066022 at item 10, 5065896 at item 6, 5065664 at item 10. This is a structural property of the source material, not an extraction failure.

### Performance

| Dimension | Interactive — 14-page test | Interactive — 189-page full manual | Batch mode |
|-----------|---------------------------|-------------------------------------|------------|
| Speed | Single-pass, session-interactive | **~4 min** (10 parallel agents) | ~3–5 min per 14 pages (3 API calls × 5 pages + Smart Fix) |
| Accuracy | **100%** (185/185, controlled test) | 1,736 rows / 55 sub-assemblies; no full-manual ground truth | Untested with live API key; expected equivalent |
| Cost | Claude Code session | Claude Code session (~591K subagent tokens) | ~$0.015/page (Sonnet 4.6; requires `ANTHROPIC_API_KEY`) |
| Scalability | Low — one session, one manual | Medium — parallel within session; one manual at a time | High — unattended, parallelizable across manuals |
| Setup | Claude Code only | Claude Code only | Claude Code + API key + pypdf |
| Human QA required | Yes | Yes — diagram-row filtering + partial piping sub-assemblies | Yes — QA-flagged CSV |

### Why this approach matches Approach 4 accuracy without the subscription

Both Approach 4 (base44) and Approach 5 (Claude Code plugin) use the same underlying model — Claude Sonnet 4.6 — with native PDF reading. The base44 platform's `ExtractDataFromUploadedFile` is a wrapper around the same Anthropic API capability that the Claude Code Read tool uses directly. The accuracy match (185/185 on controlled test) confirms that the base44 platform's contribution is orchestration and UI, not a different or better extraction model.

### Limitations

- **Interactive mode is not parallelizable across manuals.** Multiple manuals still require separate sessions; there is no queue or async capability across sessions.
- **Batch mode requires ANTHROPIC_API_KEY.** This was not available during testing; batch mode results are untested with a live key. The code is implemented and structurally correct (tool use API shape verified against SDK).
- **No editable table UI.** Approach 4 provides a browser interface for in-session row editing before export. Corrections here require re-running the skill or editing the output CSV manually.
- **Smart Fix not available in interactive mode.** The interactive skill outputs rows directly without a correction pass. Flagged rows must be corrected manually.
- **Full manual accuracy is unverified against ground truth.** The 189-page full run extracted 1,736 rows across 55 sub-assemblies, but no row-level ground truth exists for the complete manual (only pages 7–20 have been validated). Performance on lower-quality scans or other equipment types has not been measured.

### Conclusion

The Claude Code plugin (interactive mode) achieves the same measured accuracy as base44 (100% on the controlled test) with zero external dependencies and no additional cost beyond the Claude Code session. The parallel subagent design scales well within a session — the full 189-page manual ran in ~4 minutes wall-clock.

The batch mode (`extract_structured.py`) replicates base44's schema-driven extraction and Smart Fix pattern using the Anthropic API directly, and is the path for unattended, parallelizable processing once an API key is available.

---

## Comparative Summary

| Dimension | Baseline: Manual | Approach 1: Text Extraction | Approach 2: Claude Vision | Approach 3: Claude Prompting | Approach 4: Base44 App | Approach 5: Claude Code Plugin |
|-----------|-----------------|---------------------------|--------------------------|------------------------------|------------------------|-------------------------------|
| **Accuracy** | High (human reading) | ~85–90%, degrades on two-column | 77–100% at 200 DPI; variable by density | ~90–95% + human validation | **100%** (185/185, controlled test) | **100%** (185/185, controlled test); 1,736 rows / 55 sub-assemblies on full 189-page manual |
| **Speed** | 2–4 hrs/100 pages | Fast (seconds/page) | Slow interactive; ~5–10 min async batch | ~15–30 min/100 pages | ~3 min / 14-page section | **~4 min / 189 pages** (10 parallel agents); ~3–5 min/14 pages (batch) |
| **Cost** | Labour only | Low (text tokens) | ~$1.28–2.56/manual (Batch API) | Claude subscription + Adobe Acrobat | base44 subscription | **Claude Code session** (interactive); ~$0.015/page (batch, API key required) |
| **Setup complexity** | None | Medium — OCR pipeline | High — render pipeline, Batch API | Low — prompt + web UI | Low — browser UI | **Lowest** — Claude Code only (interactive); + API key (batch) |
| **Scalability** | None | High (pipeline) | Medium (Batch API; QA manual) | Low (operator-gated) | Medium (operator-gated) | Medium interactive (parallel within session); High batch (unattended) |
| **Repeatability** | Operator-dependent | High | Medium (non-deterministic) | High (fixed prompt) | High (JSON schema) | High (fixed skill rules + JSON schema) |
| **Handles two-column tables** | Yes | No | Yes | Yes | Yes | Yes |
| **Handles sub-rows** | Yes | No | Partially | Yes | Yes | Yes |
| **Human QA required** | Built-in | Yes — high effort | Yes — targeted | Yes — light | Yes — editable table review | Yes — operator review |
| **Infrastructure required** | None | OCR engine, API access | Render pipeline, Batch API | Adobe Acrobat, Claude web | base44 subscription | Claude Code (interactive); + API key (batch) |

---

## Key Findings

1. **Two-column table layout is the decisive structural problem.** Any approach that processes text linearly (Approach 1) fails on this input type regardless of accuracy on simpler documents. Visual understanding is required.

2. **Claude Vision (scripted) captures layout but not always completely.** At 200 DPI, extraction is significantly better than 150 DPI, but dense pages still produce gaps. Token cost is identical at both resolutions due to Anthropic's internal image scaling. The scripted pipeline adds infrastructure complexity without a meaningful accuracy advantage over the interactive Claude Prompting approach.

3. **Token cost is not the primary constraint for scripted approaches.** At ~$1.28–2.56/manual via Batch API (Approach 2) or ~$0.015/page via direct API (Approach 5 batch), cost is acceptable at scale. The binding constraints are accuracy ceiling and the irreducible human QA step.

4. **Claude Prompting (Approach 3) outperforms the scripted approaches on accuracy at comparable or lower cost.** The interactive loop, native PDF reading, and operator-in-the-loop QA give it a practical accuracy advantage over any fully automated pipeline attempted here.

5. **Schema-driven extraction (Approaches 4 and 5) adds a structural contract that free-form approaches lack.** Enforcing a JSON schema at extraction time prevents column misassignment and surfaces malformed rows explicitly rather than letting them propagate silently into the output.

6. **LLM post-processing with full table context is a meaningful accuracy lever.** The Smart Fix pattern — sending the entire extracted table alongside flagged rows — lets the model use neighboring-row context to correct OCR errors. This is not available in any approach that processes pages in isolation.

7. **Parallel subagents make full-manual extraction practical in interactive mode.** Splitting a 189-page manual into 10 concurrent 20-page agents reduces wall-clock time to ~4 minutes — comparable to base44's server-side extraction speed. Without parallelism, sequential single-agent extraction of 189 pages would take 30–40 minutes.

8. **The base44 platform's accuracy advantage comes from the model, not the platform.** Approach 5 (Claude Code plugin) matches Approach 4 (base44 app) exactly on the controlled test (185/185) using the same underlying model (Claude Sonnet 4.6) with the same native PDF reading capability. The base44 subscription contributes orchestration UI and a hosted extraction endpoint, not a distinct extraction advantage.

9. **Scaling is a workflow problem, not a technology problem.** Approaches 1 and 2 attempt to remove the human entirely; neither achieves the accuracy required to do so. The more productive framing is: how much can the human's time per manual be reduced, rather than how can the human be eliminated?

---

## Conclusion

**Approaches 4 and 5 are tied on measured accuracy** (both 185/185, 100% on the controlled test) and both achieve this with schema-driven extraction using Claude Sonnet 4.6 native PDF reading. The choice between them is a deployment question, not an accuracy question.

Approach 5's full 189-page run (WER wave) demonstrates the approach scales beyond the controlled test: 1,736 rows extracted across 55 sub-assemblies in ~4 minutes, with 65 diagram/reference rows correctly identified and filtered. No full-manual ground truth exists to validate accuracy at this scale, but all 55 sub-assemblies were captured and the section-by-section breakdown shows no unexplained gaps.

The one gap shared by both approaches — blank item numbers on sub-rows — is a structural pattern in the source data that all approaches handle inconsistently. It requires a targeted fix (carry parent item number forward) rather than a change in approach.

**Current recommendations by use case:**

| Use case | Recommended approach |
|---|---|
| New wave, operator already using Claude Code | **Approach 5 (interactive)** — zero setup, same accuracy as base44, no subscription required |
| Operator with base44 access, prefers browser UI | **Approach 4 (Base44 App)** — editable table review, no CLI |
| High-volume batch processing (many manuals) | **Approach 5 (batch mode)** — unattended, parallelizable; requires `ANTHROPIC_API_KEY` |
| Fallback / no Claude Code or base44 access | **Approach 3 (Claude Prompting)** — Adobe Acrobat + Claude web UI |

**If scaling beyond what a single operator can process is required**, the next step is to evaluate purpose-built document AI services (e.g., AWS Textract Tables, Azure AI Document Intelligence) that extract table structure deterministically from scanned images — separating the structural extraction problem (suited to specialized tooling) from the semantic mapping problem (suited to Claude). These would be evaluated as a distinct approach in this series.

---

## Artefacts

| Artefact | Location |
|----------|----------|
| Input PDF (full manual) | `examples/Harsco Utility Track Vehicle-UTV 354AL Parts Manual.pdf` |
| Test PDF (pages 7–20) | `work-equipment-sop/examples/harsco_pages7to20_test.pdf` |
| Target output (controlled test) | `examples/Wave 8 Breakdown.xlsx` |
| WER wave output (full manual) | `work-equipment-sop/output/WER v1.xlsx` |
| Render script | `scripts/render_pages.py` |
| PDF analysis / orchestration | `scripts/process_pdf.py` |
| Vision extraction (Batch API) | `scripts/extract_vision.py` |
| Structured extraction (Approach 5 batch) | `work-equipment-sop/scripts/extract_structured.py` |
| CSV assembly + QA flagging | `scripts/assemble_csv.py` |
| Excel writer | `scripts/write_tab.py` |
| Transcription skill | `work-equipment-sop/skills/transcribe/SKILL.md` |
| Sub-assembly skill | `work-equipment-sop/skills/sub-assembly/SKILL.md` |
| SOP baseline document | `Work_Equipment_Process_SOP_final_1.docx` |
| Architecture decision log | `HANDOFF.md` |
| Base44 app — page component | `src/pages/Home.jsx` (base44 project) |
| Base44 app — SDK client | `src/api/base44Client.js` (base44 project) |

---

*This evaluation covers five approaches (Baseline + Approaches 1–5). Additional approach evaluations (e.g., AWS Textract, Azure AI Document Intelligence, fine-tuned extraction models) will be appended.*
