"""
Core engine (ODIE)
==================

This is the heart of the project. ODIE works like a tiny offline "analytics engine":

1) Load dataset -> list of DisasterEvent records (immutable)
2) Build indices -> fast lookup tables
3) Maintain a *current selection* of event IDs (QueryState.active_ids)
4) Apply filters / search / sorting to update the selection
5) Generate reports from the current selection

DSA topics demonstrated here:
- Indices with sorted ID lists (supports fast intersection)
- Merge sort / quick sort for sorting records
- Heap (top-k) queries via `heapq`
- Undo/redo stacks (history of selections)
- Graph/search concepts (optional: where expressions as an AST)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable, Dict, Any
import heapq, time
from .models import DisasterEvent
from .indices import Indices, year_range_ids
from .dsa import merge_sort, quick_sort, intersect_sorted
from .query_lang import parse, Node, And, Or, Cmp

@dataclass
class QueryState:
    """Holds the current working set of event IDs (like a view)."""
    active_ids: List[int]
    last_sort: Optional[Tuple[str, str, bool]] = None

@dataclass
class ODIE:
    """Offline Disaster Intelligence Engine.

    The engine stores:
    - events: all DisasterEvent records
    - idx: precomputed indices for fast filters
    - state: current selection (list of IDs)

    Filters and sorts update `state.active_ids` only.
    """
    """Offline Disaster Intelligence Engine (ODIE)."""
    events: List[DisasterEvent]
    idx: Indices
    dataset_path: Optional[str] = None
    # Stores CLI commands (for reproducibility in reports)
    command_log: List[str] = field(default_factory=list)
    state: QueryState = field(init=False)

    # Stacks for undo/redo (store snapshots of active_ids)
    _undo: List[List[int]] = field(default_factory=list, init=False)
    _redo: List[List[int]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.state = QueryState(active_ids=list(range(len(self.events))))

    # ---------------- History (Stacks) ----------------
    def _push_history(self) -> None:
        self._undo.append(self.state.active_ids[:])
        self._redo.clear()

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(self.state.active_ids[:])
        self.state.active_ids = self._undo.pop()
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(self.state.active_ids[:])
        self.state.active_ids = self._redo.pop()
        return True

    # ---------------- Filters ----------------
    def reset(self) -> None:
        """Reset selection to all events."""
        self._push_history()
        self.state = QueryState(active_ids=list(range(len(self.events))))

    def filter_country(self, country: str) -> None:
        """Filter current selection to a specific country."""
        self._push_history()
        ids = self.idx.by_country.get(country, [])
        self.state.active_ids = intersect_sorted(sorted(self.state.active_ids), ids)

    def filter_type(self, dtype: str) -> None:
        """Filter current selection to a disaster type (e.g., Earthquake)."""
        self._push_history()
        ids = self.idx.by_type.get(dtype, [])
        self.state.active_ids = intersect_sorted(sorted(self.state.active_ids), ids)

    def filter_year_range(self, y1: int, y2: int) -> None:
        self._push_history()
        ids = year_range_ids(self.idx, y1, y2)
        self.state.active_ids = intersect_sorted(sorted(self.state.active_ids), ids)

    def where(self, expr: str) -> None:
        """Apply boolean expression to current result set."""
        self._push_history()
        ast = parse(expr)
        self.state.active_ids = self._eval_node(ast, self.state.active_ids)

    # ---------------- Query language evaluation ----------------
    def _eval_node(self, node: Node, candidate_ids: List[int]) -> List[int]:
        if isinstance(node, And):
            left_ids = self._eval_node(node.left, candidate_ids)
            return self._eval_node(node.right, left_ids)
        if isinstance(node, Or):
            left_ids = self._eval_node(node.left, candidate_ids)
            right_ids = self._eval_node(node.right, candidate_ids)
            return _union_sorted(left_ids, right_ids)
        if isinstance(node, Cmp):
            return self._apply_cmp(node, candidate_ids)
        raise ValueError("Unknown AST node")

    def _apply_cmp(self, cmp: Cmp, candidate_ids: List[int]) -> List[int]:
        field = cmp.field.lower()
        op = cmp.op

        # Index-based equality for categorical fields
        if op == "==" and field in ("country", "disaster_type"):
            ids = self.idx.by_country.get(str(cmp.value), []) if field == "country" else self.idx.by_type.get(str(cmp.value), [])
            return intersect_sorted(sorted(candidate_ids), ids)

        # Index-based year constraints (start_year)
        if field in ("start_year", "year"):
            if op == "==":
                ids = self.idx.year_to_ids.get(int(cmp.value), [])
                return intersect_sorted(sorted(candidate_ids), ids)
            if op in (">=", ">", "<=", "<"):
                years = self.idx.years_sorted
                if not years:
                    return []
                lo = years[0]; hi = years[-1]
                v = int(cmp.value)
                if op == ">=":
                    lo = v
                elif op == ">":
                    lo = v + 1
                elif op == "<=":
                    hi = v
                elif op == "<":
                    hi = v - 1
                ids = year_range_ids(self.idx, lo, hi)
                return intersect_sorted(sorted(candidate_ids), ids)

        # Fallback scan
        pred = _make_predicate(cmp)
        out: List[int] = []
        for eid in candidate_ids:
            if pred(self.events[eid]):
                out.append(eid)
        out.sort()
        return out

    # ---------------- Output operations ----------------
    def _events_from_ids(self, ids: List[int]) -> List[DisasterEvent]:
        return [self.events[i] for i in ids]

    def sort(self, field: str, algo: str = "merge", reverse: bool = True) -> List[DisasterEvent]:
        key = _field_key(field)
        arr = self._events_from_ids(self.state.active_ids)
        if algo == "merge":
            out = merge_sort(arr, key=key, reverse=reverse)
        elif algo == "quick":
            out = quick_sort(arr, key=key, reverse=reverse)
        else:
            raise ValueError("algo must be 'merge' or 'quick'")
        self.state.last_sort = (field, algo, reverse)
        return out

    def topk(self, k: int, field: str) -> List[DisasterEvent]:
        key = _field_key(field)
        heap: List[tuple] = []
        for eid in self.state.active_ids:
            e = self.events[eid]
            v = key(e)
            if v is None:
                continue
            if len(heap) < k:
                heapq.heappush(heap, (v, eid))
            else:
                if v > heap[0][0]:
                    heapq.heapreplace(heap, (v, eid))
        heap.sort(reverse=True)
        return [self.events[eid] for _, eid in heap]

    def export_csv(self, path: str) -> None:
        import csv
        rows = self._events_from_ids(self.state.active_ids)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["event_id","dis_no","country","disaster_type","disaster_subtype",
                        "start_year","start_month","start_day",
                        "total_deaths","total_affected","total_damage_adj_usd"])
            for e in rows:
                w.writerow([e.event_id, e.dis_no, e.country, e.disaster_type, e.disaster_subtype,
                            e.start_year, e.start_month, e.start_day,
                            e.total_deaths, e.total_affected, e.total_damage_adj_usd])

    
    def export_json(self, path: str) -> None:
        """Export the current selection to a JSON file.

        CSV is great for spreadsheets; JSON is great for programs and preserves field names.
        """
        import json
        rows = self._events_from_ids(self.state.active_ids)
        payload = [
            {
                "event_id": e.event_id,
                "dis_no": e.dis_no,
                "country": e.country,
                "disaster_type": e.disaster_type,
                "disaster_subtype": e.disaster_subtype,
                "start_year": e.start_year,
                "start_month": e.start_month,
                "start_day": e.start_day,
                "total_deaths": e.total_deaths,
                "total_affected": e.total_affected,
                "total_damage_adj_usd": e.total_damage_adj_usd,
            }
            for e in rows
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

def bench(self, country: str, dtype: str, y1: int, y2: int, rounds: int = 30) -> Dict[str, float]:
        def naive():
            ids = []
            for e in self.events:
                if e.country == country and e.disaster_type == dtype and (y1 <= e.start_year <= y2):
                    ids.append(e.event_id)
            return ids

        def indexed():
            ids = self.idx.by_country.get(country, [])
            ids = intersect_sorted(ids, self.idx.by_type.get(dtype, []))
            ids = intersect_sorted(ids, year_range_ids(self.idx, y1, y2))
            return ids

        t0 = time.perf_counter()
        for _ in range(rounds): naive()
        t1 = time.perf_counter()
        for _ in range(rounds): indexed()
        t2 = time.perf_counter()
        return {"naive_ms": (t1-t0)*1000/rounds, "indexed_ms": (t2-t1)*1000/rounds}

# ---------------- Helpers ----------------
def _union_sorted(left_ids: List[int], right_ids: List[int]) -> List[int]:
    a = sorted(left_ids); b = sorted(right_ids)
    i = j = 0
    out: List[int] = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            out.append(a[i]); i += 1; j += 1
        elif a[i] < b[j]:
            out.append(a[i]); i += 1
        else:
            out.append(b[j]); j += 1
    out.extend(a[i:]); out.extend(b[j:])
    # unique
    uniq: List[int] = []
    prev = None
    for x in out:
        if prev != x:
            uniq.append(x); prev = x
    return uniq

def _field_key(field: str) -> Callable[[DisasterEvent], object]:
    f = field.lower().strip()
    if f in ("deaths","total_deaths"):
        return lambda e: e.total_deaths if e.total_deaths is not None else -1
    if f in ("affected","total_affected"):
        return lambda e: e.total_affected if e.total_affected is not None else -1
    if f in ("damage","damages","total_damage","total_damage_adj_usd"):
        return lambda e: e.total_damage_adj_usd if e.total_damage_adj_usd is not None else -1.0
    if f in ("year","start_year"):
        return lambda e: e.start_year
    if f in ("date","start_date"):
        return lambda e: e.start_date_key()
    raise ValueError("field must be: deaths, affected, damage, year, date")

def _make_predicate(cmp: Cmp) -> Callable[[DisasterEvent], bool]:
    field = cmp.field
    op = cmp.op
    val = cmp.value

    def get(e: DisasterEvent) -> Any:
        fname = field.lower()
        if fname == "country":
            return e.country
        if fname in ("type", "disaster_type"):
            return e.disaster_type
        if fname in ("subtype", "disaster_subtype"):
            return e.disaster_subtype
        if fname in ("start_year","year"):
            return e.start_year
        if fname in ("total_deaths","deaths"):
            return e.total_deaths if e.total_deaths is not None else -1
        if fname in ("total_affected","affected"):
            return e.total_affected if e.total_affected is not None else -1
        if fname in ("damage","total_damage_adj_usd","damages"):
            return e.total_damage_adj_usd if e.total_damage_adj_usd is not None else -1.0
        if fname in ("dis_no","disno"):
            return e.dis_no
        return getattr(e, fname, None)

    if op == "contains":
        sval = str(val).lower()
        return lambda e: sval in str(get(e)).lower()

    if op == "==": return lambda e: get(e) == val
    if op == "!=": return lambda e: get(e) != val
    if op == ">=": return lambda e: get(e) >= val
    if op == "<=": return lambda e: get(e) <= val
    if op == ">":  return lambda e: get(e) > val
    if op == "<":  return lambda e: get(e) < val

    raise ValueError(f"Unsupported operator: {op}")
