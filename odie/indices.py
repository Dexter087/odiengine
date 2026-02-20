"""
Indices (precomputed lookup tables)
===================================

ODIE builds simple indices (maps from value -> list of row IDs) to make
common filters fast.

Example:
- `by_country["India"]` gives a sorted list of row IDs for India.
- `year_to_ids[2001]` gives IDs for all disasters that started in 2001.

Why sorted lists?
- Sorted ID lists allow fast intersections using the two-pointer technique.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List
from bisect import bisect_left, bisect_right
from .models import DisasterEvent

@dataclass
class Indices:
    """Container of precomputed indices for fast filtering."""
    by_country: Dict[str, List[int]]
    by_type: Dict[str, List[int]]
    year_to_ids: Dict[int, List[int]]
    years_sorted: List[int]

def build_indices(events: List[DisasterEvent]) -> Indices:
    """Build indices from the loaded dataset.

    Returns:
        Indices object containing maps like by_country, by_type, year_to_ids.
    """
    by_country: Dict[str, List[int]] = {}
    by_type: Dict[str, List[int]] = {}
    year_to_ids: Dict[int, List[int]] = {}

    for e in events:
        by_country.setdefault(e.country, []).append(e.event_id)
        by_type.setdefault(e.disaster_type, []).append(e.event_id)
        year_to_ids.setdefault(e.start_year, []).append(e.event_id)

    for d in (by_country, by_type, year_to_ids):
        for k in d:
            d[k].sort()

    years_sorted = sorted(year_to_ids.keys())
    return Indices(by_country=by_country, by_type=by_type, year_to_ids=year_to_ids, years_sorted=years_sorted)

def year_range_ids(idx: Indices, y1: int, y2: int) -> List[int]:
    """Return sorted event IDs with start_year in [y1, y2].

    We use binary search on `years_sorted` and then merge the ID lists.
    """
    # Find the slice of years that fall inside the range
    lo = bisect_left(idx.years_sorted, y1)
    hi = bisect_right(idx.years_sorted, y2)
    out: List[int] = []
    for y in idx.years_sorted[lo:hi]:
        out.extend(idx.year_to_ids.get(y, []))
    out.sort()
    return out
