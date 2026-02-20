ODIE — Offline Disaster Intelligence Engine (CLI)
=================================================

Author: Daksha Mothukuri
Course: Programming & Data Structures (DSA / PDS)
Project Type: Offline CLI data exploration engine for EM-DAT Excel exports

ODIE is a command-line tool that loads a non-updating Excel dataset (EM-DAT export),
lets you explore it interactively using filters and a `where` query language, and generates
outputs like DOCX reports (with plots) and CSV/JSON exports.


1) What ODIE can do
------------------
- Load an EM-DAT Excel export (.xlsx) fully offline
- Interactive CLI with commands like:
  - filter by country, disaster type, year range
  - advanced filtering using a `where` query language (boolean conditions)
  - sort results by numeric/date fields
  - show top-k results (heap-based)
  - undo/redo exploration steps (history stacks)
- Generate a DOCX report for the selected subset (with matplotlib graphs)
- Export the selected subset to CSV / JSON


2) Tech / DSA concepts used
-----------------------------------------------
- OOP: structured classes for events + engine state
- Searching: binary search (bisect) for year-range slicing
- Sorting: ordering subsets by chosen key fields
- Stacks: undo/redo history
- Trees: parsing `where` into an expression tree (AST)
- Heaps (priority queue): top-k retrieval


3) Repository layout (how to navigate)
--------------------------------------
Typical layout:

- odie/
  - cli.py       : entry point, REPL loop, command parsing/dispatch
  - engine.py    : core logic, maintains active selection of record IDs
  - loader.py    : reads .xlsx, converts to in-memory event objects
  - models.py    : data model (DisasterEvent)
  - indices.py   : precomputed indices (country/type/year -> record IDs)
  - query_lang.py: tokenizer + parser + AST evaluation for where
  - report.py    : DOCX report generation + plots
  - export.py    : CSV/JSON exporting
  - dsa.py       : helper routines (intersection, etc.)
- requirements.txt : dependencies


4) Setup
--------
4.1) Create a virtual environment (recommended)

Windows (PowerShell):
  python -m venv .venv
  .venv\Scripts\activate

macOS/Linux:
  python -m venv .venv
  source .venv/bin/activate

4.2) Install dependencies
  pip install -r requirements.txt


5) Running ODIE
---------------
From the project root (the folder containing odie/):

  python -m odie.cli --xlsx "PATH_TO_YOUR_EXCEL_FILE.xlsx"

Example (Windows):
  python -m odie.cli --xlsx "C:\Users\Daksh\Downloads\public_emdat_custom_request.xlsx"

If successful, you’ll see:
  Loading dataset...
  Loaded XXXXX events. Type 'help' for commands.
  odie>


6) Core concept: “active selection” (what ODIE changes)
-------------------------------------------------------
ODIE never edits your Excel file.
It loads the dataset into memory and maintains an internal active selection (a subset of record IDs).
Every filter / query updates only that selection. Reports and exports are generated from the current selection.


7) Commands (full guide)
------------------------
7.1) help
Shows available commands.
  help

7.2) stats
Shows dataset summary (count, common types, etc.).
  stats

7.3) show
Displays a small preview table of the current selection.
  show
  show 20

7.4) reset
Resets selection back to the full dataset.
  reset


8) Filtering commands
---------------------
8.1) filter country
Filters current selection by country.
  filter country "India"
  filter country "United States of America"

8.2) filter type
Filters current selection by disaster type.
  filter type "Flood"
  filter type "Earthquake"

8.3) filter year
Filters selection to a year range (inclusive).
  filter year 2000 2020

NOTE: If your build uses a slightly different name, type `help` and use the year-range command shown there.


9) Advanced filtering: where (VERY IMPORTANT SYNTAX)
----------------------------------------------------
Correct usage:
- Do NOT wrap the whole expression in quotes.
- Use lowercase boolean operators: and / or / not

Works:
  where country == 'India' and disaster_type == 'Flood' and start_year >= 2000 and start_year <= 2020

Incorrect (causes: Expected IDENT, got STRING):
  where "country == 'India' and disaster_type == 'Flood'"

Operators supported (typical):
- Comparisons: ==, !=, <, <=, >, >=
- Boolean: and, or, not

Strings:
- Use single quotes for text values:
  country == 'India'


10) Sorting
-----------
sort: sorts the current selection by a field.
  sort deaths desc
  sort deaths asc
  sort start_year asc

If a field is missing (None), ODIE handles it safely (typically treated as smallest).


11) Top-k (largest K results)
-----------------------------
topk: shows top-k events by a numeric field using a heap-based approach.
  topk 10 deaths
  topk 20 damage


12) History (Undo/Redo)
-----------------------
ODIE maintains history so you can step backward/forward.
  undo
  redo


13) Exporting
-------------
13.1) export csv
Exports current selection to a CSV file.
  export csv "subset.csv"

13.2) export json
Exports current selection to JSON.
  export json "subset.json"


14) Report generation (DOCX)
----------------------------
report: generates a DOCX report for the current selection, including plots.
  report "my_report.docx" current

Recommended flow before reporting:
  filter country "India"
  filter type "Flood"
  filter year 2000 2020
  report "India_Flood_2000_2020.docx" current


15) Example demo session (good for your 3-minute code video)
-----------------------------------------------------------
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


16) Common errors + fixes
-------------------------
16.1) No module named 'docx'
Cause: dependencies not installed.
Fix:
  pip install -r requirements.txt

16.2) Expected IDENT, got STRING (in where)
Cause: you wrapped the whole condition in quotes.
Fix: remove outer quotes and use lowercase and/or.
  where country == 'India' and start_year >= 2000

16.3) Excel columns not found
Cause: EM-DAT exports can differ in column names.
Fix: update column mapping in odie/loader.py (ODIE tries multiple variants, but a custom export may require updates).


17) Dataset citation (for your repo / report)
---------------------------------------------
EM-DAT: The International Disaster Database — CRED / UCLouvain.
Website: https://www.emdat.be
