"""
ODIE Command Line Interface (CLI)
=================================

This file provides the interactive terminal program you run like:

    python -m odie.cli --xlsx "path/to/emdat.xlsx"

It demonstrates:
- Argument parsing (argparse)
- A REPL loop (Read-Eval-Print Loop) for commands
- Mapping user commands to engine methods (filters, sort, search, report)

The CLI DOES NOT modify your dataset file. It only loads it once and works on
an in-memory selection of records.
"""

from __future__ import annotations
import argparse, shlex
from .loader import load_emdat_xlsx
from .indices import build_indices
from .engine import ODIE

# -----------------------------
# Help text (grouped, with examples)
# -----------------------------
HELP_TEXT = """
ODIE commands (grouped)
----------------------

1) View / Inspect
   help
   show all | show current
   stats
   values <field>                   (example: values country)

2) Filtering (fast via indices)
   filter country "<Country>"       (example: filter country "India")
   filter type "<Disaster Type>"    (example: filter type "Earthquake")
   filter year <y1> <y2>            (example: filter year 2000 2010)
   where "<expr>"                   (example: where "deaths > 1000 and year >= 2000")

3) Sorting / Top-k
   sort <field> [asc|desc]          (example: sort deaths desc)
   topk <k> <field>                 (example: topk 10 deaths)

4) Export (current selection)
   export csv "<out.csv>"           (example: export csv "subset.csv")
   export json "<out.json>"         (example: export json "subset.json")

5) Report (DOCX)
   report "<out.docx>" current      (example: report "my_report.docx" current)

6) History
   undo
   redo

7) Benchmarking (for DSA demonstration)
   bench country "<Country>" "<Type>" <y1> <y2> [rounds]
   example: bench country "India" "Earthquake" 2000 2010 50

8) Exit
   quit
"""

HELP = """
Commands:
  help
  stats
  reset
  undo
  redo

  filter country "<Country>"
  filter type "<Disaster Type>"
  filter year <y1> <y2>

  where "<expr>"
    - boolean expression: AND / OR, parentheses
    - operators: == != >= <= > < contains
    Example:
      where "country == 'India' AND disaster_type == 'Flood' AND start_year >= 2000 AND start_year <= 2020 AND total_deaths > 100"

  values country [prefix]
  values type [prefix]

  sort <field> [merge|quick] [asc|desc]
  topk <k> <field>
  export "<path.csv>"
  bench "<Country>" "<Disaster Type>" <y1> <y2>
  report "<path.docx>" [current|full]
  show [n]
  quit

Fields: deaths, affected, damage, year, date
where fields: country, disaster_type, disaster_subtype, start_year, total_deaths, total_affected, total_damage_adj_usd, dis_no
"""


def __make_citation(engine):
    from .report import DatasetCitation
    import os
    p = getattr(engine, "dataset_path", None)
    fn = os.path.basename(p) if p else None
    return DatasetCitation(file_name=fn)


def main():
    """Entry point for the ODIE CLI.

    1) Load dataset
    2) Build indices
    3) Start an interactive REPL
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", required=True, help="Path to EM-DAT excel export")
    args = ap.parse_args()

    print("Loading dataset...")
    events = load_emdat_xlsx(args.xlsx)
    idx = build_indices(events)
    engine = ODIE(events=events, idx=idx)
    engine.dataset_path = args.xlsx

    print(f"Loaded {len(events)} events. Type 'help' for commands.")
    while True:
        try:
            line = input("odie> ")
            # Read one command from the user (REPL input).
            # Keep a lightweight log of commands for the report (reproducibility).
            stripped = line.strip()
            if stripped:
                cmd0 = stripped.split()[0].lower()
                if cmd0 not in ("help", "show", "values", "stats", "quit"):
                    engine.command_log.append(stripped)
        except EOFError:
            break
        if not line:
            continue
        if line.lower() in ("quit","exit"):
            break
        if line.lower() == "help":
            print(HELP); continue
        try:
            handle(engine, line)
        except Exception as e:
            print(f"Error: {e}")

def handle(engine: ODIE, line: str) -> None:
    """Handle one CLI command line.

    This parses the command and calls the appropriate engine method.
    """
    # allow where without needing shell-style quoting
    if line.lower().startswith("where "):
        expr = line[len("where "):].strip()
        engine.where(expr)
        print(f"Applied where-filter. Size={len(engine.state.active_ids)}")
        return

    parts = shlex.split(line)
    cmd = parts[0].lower()

    if cmd == "help":
        print(HELP_TEXT)
        return

    if cmd == "stats":
        print(f"Current result size: {len(engine.state.active_ids)}")
        print(f"Countries: {len(engine.idx.by_country)} | Types: {len(engine.idx.by_type)} | Years: {len(engine.idx.years_sorted)}")
        return

    if cmd == "reset":
        engine.reset()
        print("State reset.")
        return

    if cmd == "undo":
        print("Undone." if engine.undo() else "Nothing to undo.")
        return

    if cmd == "redo":
        print("Redone." if engine.redo() else "Nothing to redo.")
        return

    if cmd == "values":
        field = parts[1].lower()
        prefix = parts[2] if len(parts) >= 3 else ""
        if field == "country":
            vals = sorted(engine.idx.by_country.keys())
        elif field == "type":
            vals = sorted(engine.idx.by_type.keys())
        else:
            raise ValueError("values field must be: country | type")
        if prefix:
            p = prefix.lower()
            vals = [v for v in vals if v.lower().startswith(p)]
        for v in vals[:50]:
            print(v)
        if len(vals) > 50:
            print(f"... ({len(vals)} total, showing 50)")
        return

    if cmd == "filter":
        kind = parts[1].lower()
        if kind == "country":
            c = parts[2]; engine.filter_country(c); print(f"Filtered country={c}. Size={len(engine.state.active_ids)}"); return
        if kind == "type":
            t = parts[2]; engine.filter_type(t); print(f"Filtered type={t}. Size={len(engine.state.active_ids)}"); return
        if kind == "year":
            y1, y2 = int(parts[2]), int(parts[3]); engine.filter_year_range(y1,y2); print(f"Filtered years {y1}-{y2}. Size={len(engine.state.active_ids)}"); return
        raise ValueError("filter kind must be: country, type, year")

    if cmd == "sort":
        field = parts[1]
        algo = parts[2].lower() if len(parts) >= 3 and parts[2].lower() in ("merge","quick") else "merge"
        order = parts[3].lower() if len(parts) >= 4 and parts[3].lower() in ("asc","desc") else "desc"
        reverse = (order == "desc")
        out = engine.sort(field=field, algo=algo, reverse=reverse)
        print(f"Sorted {len(out)} events by {field} using {algo} ({order}). Showing 10:")
        _print_rows(out[:10]); return

    if cmd == "topk":
        k = int(parts[1]); field = parts[2]
        out = engine.topk(k, field)
        print(f"Top {len(out)} by {field}:")
        _print_rows(out); return

    if cmd == "report":
        # report "<path.docx>" [current|full]
        from .report import generate_docx_report, ReportConfig
        path = parts[1]
        scope = parts[2].lower() if len(parts) >= 3 else "current"
        if scope not in ("current", "full"):
            raise ValueError("report scope must be: current | full")
        if scope == "full":
            evs = engine.events
            label = "Full Dataset"
        else:
            evs = [engine.events[i] for i in engine.state.active_ids]
            label = "Current Result Set"
        cfg = ReportConfig(
            title="ODIE Report",
            subtitle="Offline Disaster Intelligence Engine (CLI)",
            dataset_name="EM-DAT Excel export",
            citation=__make_citation(engine),
            command_log=engine.command_log,
        )
        generate_docx_report(evs, path, config=cfg, scope_label=label)
        print(f"Report written to {path}")
        return

    if cmd == "export":
        # export <csv|json> "<path>"
        # Examples:
        #   export csv "subset.csv"
        #   export json "subset.json"
        if len(parts) < 3:
            print('Usage: export csv "out.csv"  OR  export json "out.json"')
            return

        fmt = parts[1].lower()
        out_path = parts[2]

        # If the user typed quotes, remove them safely
        if len(out_path) >= 2 and out_path[0] in ('"', "'") and out_path[-1] == out_path[0]:
            out_path = out_path[1:-1]

        if not engine.state.active_ids:
            print("Nothing to export: current selection is empty.")
            return

        if fmt == "csv":
            engine.export_csv(out_path)
            print(f"Exported CSV to {out_path}")
            return

        if fmt == "json":
            engine.export_json(out_path)
            print(f"Exported JSON to {out_path}")
            return

        print("Unknown export format. Use: csv or json")
        return

    if cmd == "bench":
        c, t, y1, y2 = parts[1], parts[2], int(parts[3]), int(parts[4])
        res = engine.bench(c, t, y1, y2)
        print(f"naive={res['naive_ms']:.3f}ms | indexed={res['indexed_ms']:.3f}ms")
        return

    if cmd == "show":
        n = int(parts[1]) if len(parts) >= 2 else 10
        rows = [engine.events[i] for i in engine.state.active_ids[:n]]
        _print_rows(rows); return

    print("Unknown command. Type 'help'.")
    return

def _print_rows(rows):
    for e in rows:
        print(f"[{e.event_id}] {e.country} | {e.disaster_type}/{e.disaster_subtype} | {e.start_year} | deaths={e.total_deaths} affected={e.total_affected} damage_adj={e.total_damage_adj_usd}")

if __name__ == "__main__":
    main()
