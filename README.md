# Parts Manual Extractor

> **Co-op project** — built during a software engineering co-op at Keolis, a railway operations and maintenance company.

A Claude Code plugin that extracts structured parts data from scanned equipment manuals and writes the results directly to Excel — reducing a 2–4 hour manual data entry task to roughly 15 minutes of review.

---

## Background

Keolis maintains a fleet of railway work equipment — track vehicles, utility machines, and support equipment. For each piece of equipment, a detailed parts manual exists as a scanned PDF. To support maintenance planning, every part in every manual needs to be entered into **Trapeze**, the company's maintenance management system.

That means someone has to open the PDF, read each table page, and type every row — item number, part description, part number, quantity — into a spreadsheet, one by one.

For a single 189-page manual, that's an estimated **2–4 hours of work**.

The goal of this project was to answer a simple question: **can AI automate this?**

---

## The Challenge

The manuals are scanned image PDFs — no embedded text, no machine-readable layer. Standard document tools can't parse them. But the structural complexity goes beyond that:

- **Two-column table layout** — each page splits parts into a left and right column. Text recognition software reads top-to-bottom and interleaves the two columns, producing output that's nearly impossible to reconstruct correctly.
- **~80% of pages are diagrams** — full-page technical illustrations with no parts data. Any pipeline must distinguish these from data pages without missing real content.
- **Sub-assemblies span multiple pages** — a section header appears once; continuation pages carry no label. The pipeline must track context across page boundaries.
- **Part numbers are fragile** — industrial codes like `0-3582001-0-18` are easily corrupted by character recognition errors (O↔0, l↔1). An incorrect part number causes ordering failures downstream.

The two-column layout proved to be the decisive problem. Any approach that processed the document as a text stream failed here — regardless of how sophisticated the downstream processing was.

---

## Evaluation: Five Approaches

This project wasn't built in one go. It went through five distinct approaches, each addressing the failures of the previous one.

| Approach | Method | Accuracy | Time |
|---|---|---|---|
| Baseline | Manual copy-paste | High | 2–4 hrs / 100 pages |
| 1 · Text recognition | OCR software → AI text processing | ~87% | Seconds/page |
| 2 · AI image reading | Convert pages to images → AI vision | 77–100% | 5–10 min batch |
| 3 · Operator + AI *(current)* | Operator prompts Claude web UI | ~92% + review | 15–30 min / 100 pages |
| 4 · AI app (base44) | Schema-driven browser app | 100% | ~3 min |
| **5 · This plugin** | In-house Claude Code plugin | **100%** | **~4 min / 189 pages** |

**Approach 1** was fast but structurally broken — the two-column layout made the OCR output too garbled for reliable reconstruction.

**Approach 2** improved dramatically by having AI read the pages visually rather than as text. But without a structured output contract, errors were silent — a missing row looked the same as a row that was never there.

**Approach 3** is what the team uses today: an operator uploads the PDF to Claude's web interface and prompts it to extract. Accuracy is good, but it's still gated on operator time and can't be parallelized across manuals.

**Approach 4** (base44) introduced the key breakthrough: a strict output schema that forces the AI to return a validated structure. Errors surface explicitly instead of silently. Accuracy hit 100% on the controlled test. But it requires a third-party subscription and a browser-based workflow.

**Approach 5** — this plugin — replicates that same accuracy in-house. No subscription, no external dependency, and it runs ten sections of the manual simultaneously, completing a full 189-page manual in about four minutes.

---

## How It Works

The plugin is a set of Claude Code slash commands. The operator runs one command; the plugin handles the rest.

For large manuals (over 30 pages), it splits the PDF into 20-page sections and reads all of them simultaneously — like having multiple people read different chapters at the same time. Each section takes 3–4 minutes; the whole manual is done when the slowest section finishes.

The two structural breakthroughs that made 100% accuracy possible:

1. **AI reads the PDF natively** — no conversion step. The AI sees the visual layout, handles two-column tables correctly, and automatically skips diagram pages.
2. **Strict output schema** — the AI must return a validated structure for every row. Anything that doesn't match is flagged for the operator to review, rather than silently accepted.

---

## Outcome

Tested on the Harsco Utility Track Vehicle 354AL Parts Manual (189 pages):

- **1,736 parts rows** extracted and written to Excel
- **55 sub-assemblies** identified and classified
- **100% row capture** on the controlled validation test (185/185 rows)
- **~4 minutes** wall-clock time for the full manual
- **No additional cost** — runs within an existing Claude Code session

The operator's role shifts from spending hours on data entry to spending 10–15 minutes reviewing the output before upload.

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

Install the plugin in Claude Code:

```
/plugins install .
```

Output is written to `output/<WAVE>.xlsx` with three tabs: **Parts**, **Sub-Assemblies**, and **High-Level**.

---

## Further Reading

- [`docs/evaluation_automation_approach.md`](docs/evaluation_automation_approach.md) — full technical write-up of all five approaches, results, and findings
- [`docs/evaluation_presentation.html`](docs/evaluation_presentation.html) — slide deck covering the evolution, challenges, and learnings (open in a browser)
