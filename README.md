# ODIE — Offline Disaster Intelligence Engine (CLI)

**Author:** Daksha Mothukuri  
**Course:** Programming & Data Structures (DSA)  
**Project:** Offline CLI data exploration engine for an EM-DAT Excel export

ODIE is a **command-line tool** that loads a **non-updating EM-DAT `.xlsx` dataset** (offline), lets you explore it interactively using **filters** and an advanced **`where` query language**, and generates outputs like **DOCX reports (with plots)** and **CSV/JSON exports**.

---

## Key Features

- Offline loading of EM-DAT Excel export (`.xlsx`)
- Interactive CLI (REPL) with:
  - country/type/year-range filtering
  - advanced boolean filtering using `where`
  - sorting (asc/desc) by chosen fields
  - top-k retrieval (heap-based)
  - undo/redo history
- Output generation:
  - DOCX report with matplotlib graphs
  - export current subset to CSV / JSON

---

## DSA Concepts Used

- **OOP**: structured event model + engine state
- **Searching**: binary search (`bisect`) for year-range slicing
- **Sorting**: ordering subsets by key fields
- **Stacks**: undo/redo history
- **Trees**: parsing and evaluating `where` queries via an AST
- **Heaps (Priority Queue)**: top-k retrieval

---

## Project Structure

```
odie/
  cli.py        # Entry point, REPL loop, command parsing/dispatch
  engine.py     # Core logic, maintains active selection of record IDs
  loader.py     # Reads .xlsx, creates in-memory event objects
  models.py     # Data model (DisasterEvent)
  indices.py    # Precomputed indices (country/type/year -> record IDs)
  query_lang.py # Tokenizer + parser + AST evaluation for `where`
  report.py     # DOCX report generation + plots
  export.py     # CSV/JSON exporting (if present in your version)
  dsa.py        # Helper routines (intersection, etc.)
requirements.txt
```

---

## Setup

### 1) Create a virtual environment (recommended)

**Windows (PowerShell):**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

---

## Run ODIE

From the project root (folder containing `odie/`):

```bash
python -m odie.cli --xlsx "PATH_TO_DATASET.xlsx"
```

**Example (Windows):**
```bash
python -m odie.cli --xlsx "C:\Users\Daksh\Downloads\public_emdat_custom_request.xlsx"
```

Expected startup:
```
Loading dataset...
Loaded XXXXX events. Type 'help' for commands.
odie>
```

---

## Core Idea: “Active Selection” (ODIE does NOT edit Excel)

ODIE treats the Excel file as **read-only**.

It loads the dataset into memory and maintains an internal **active selection** (subset of record IDs).  
Filters/queries only update this selection. Reports and exports are generated from the current selection.

---

## Commands (Quick Reference)

### General
```text
help
stats
show
show 20
reset
```

### Filtering
```text
filter country "India"
filter type "Flood"
filter year 2000 2020
```

> If your build uses a different year command name, run `help` and follow the displayed syntax.

---

## Advanced Filtering: `where` (IMPORTANT)

✅ **Do NOT wrap the full expression in quotes**.  
✅ Use lowercase boolean operators: `and`, `or`, `not`.

**Works:**
```text
where country == 'India' and disaster_type == 'Flood' and start_year >= 2000 and start_year <= 2020
```

**Wrong (causes: Expected IDENT, got STRING):**
```text
where "country == 'India' and disaster_type == 'Flood'"
```

Supported operators (typical):
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Boolean: `and`, `or`, `not`

---

## Sorting
```text
sort deaths desc
sort deaths asc
sort start_year asc
```

---

## Top-k
```text
topk 10 deaths
topk 20 damage
```

---

## Undo / Redo
```text
undo
redo
```

---

## Export
```text
export csv "subset.csv"
export json "subset.json"
```

---

## Report (DOCX)
```text
report "my_report.docx" current
```

Recommended flow:
```text
filter country "India"
filter type "Flood"
filter year 2000 2020
report "India_Flood_2000_2020.docx" current
```

---

## Example Demo Session (Good for the 3-Min Code Video)

```text
reset
stats
filter country "India"
filter type "Flood"
filter year 2000 2020
show 10
sort deaths desc
topk 10 deaths
report "demo_report.docx" current
export csv "demo_subset.csv"
```

---

## Troubleshooting

### Error: `No module named 'docx'`
Install dependencies:
```bash
pip install -r requirements.txt
```

### Error: `Expected IDENT, got STRING` (in `where`)
You wrapped the full condition in quotes. Remove outer quotes:
```text
where country == 'India' and start_year >= 2000
```

### Error: Missing Excel columns
Different EM-DAT exports may use different column names.  
Update the column mapping in `odie/loader.py` if needed.

---

## Dataset Citation

EM-DAT: The International Disaster Database — CRED / UCLouvain  
https://www.emdat.be
