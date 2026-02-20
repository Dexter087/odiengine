"""
Dataset loader (Excel -> DisasterEvent list)
============================================

This module reads the EM-DAT Excel export and converts each row into a
`DisasterEvent` object.

Key ideas:
- We try multiple possible column names because EM-DAT exports may vary.
- We keep conversion helpers (_to_int/_to_float/_to_str) to safely handle blanks.
- The loader returns a list of immutable records; ODIE never edits the Excel file.
"""

from __future__ import annotations
from typing import List, Optional
import pandas as pd
import re
from .models import DisasterEvent

def _to_int(x) -> Optional[int]:
    """Convert a cell to int, returning None if missing/invalid."""
    if pd.isna(x): return None
    try: return int(float(x))
    except Exception: return None

def _to_float(x) -> Optional[float]:
    """Convert a cell to float, returning None if missing/invalid."""
    if pd.isna(x): return None
    try: return float(x)
    except Exception: return None

def _to_str(x) -> str:
    if pd.isna(x): return ""
    return str(x).strip()

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

def _col(df: pd.DataFrame, *names: str) -> str:
    cols = list(df.columns)
    for n in names:
        if n in cols:
            return n
    norm_map = {_norm(c): c for c in cols}
    for n in names:
        nn = _norm(n)
        if nn in norm_map:
            return norm_map[nn]
    raise KeyError(f"Missing required column. Tried={names}. Available={cols}")

def _damage_adjusted_column(df: pd.DataFrame) -> Optional[str]:
    cols = list(df.columns)
    exact = "Total Damage, Adjusted ('000 US$)"
    if exact in cols:
        return exact
    exact_norm = _norm(exact)
    for c in cols:
        if _norm(c) == exact_norm:
            return c
    for c in cols:
        nc = _norm(c)
        if "totaldamage" in nc and "adjust" in nc:
            return c
    return None

def load_emdat_xlsx(path: str) -> List[DisasterEvent]:
    """
    Loader tuned for the user's EM-DAT export.
    Note: Total Damage, Adjusted ('000 US$) is converted to US$ by *1000.
    """
    df = pd.read_excel(path, engine="openpyxl")
    df.rename(columns={c: str(c).strip() for c in df.columns}, inplace=True)

    dis_no_col = _col(df, "DisNo.", "Dis No", "DisNo", "Disaster No", "Disaster Number")
    country_col = _col(df, "Country", "Country/Area", "Country / Area")
    type_col = _col(df, "Disaster Type", "Disaster type", "Type")
    subtype_col = _col(df, "Disaster Subtype", "Disaster subtype", "Disaster Sub-type", "SubType", "Disaster Sub Type")

    sy_col = _col(df, "Start Year", "Start year", "Year")
    sm_col = "Start Month" if "Start Month" in df.columns else ("Start month" if "Start month" in df.columns else None)
    sd_col = "Start Day" if "Start Day" in df.columns else ("Start day" if "Start day" in df.columns else None)

    ey_col = "End Year" if "End Year" in df.columns else ("End year" if "End year" in df.columns else None)
    em_col = "End Month" if "End Month" in df.columns else ("End month" if "End month" in df.columns else None)
    ed_col = "End Day" if "End Day" in df.columns else ("End day" if "End day" in df.columns else None)

    deaths_col = "Total Deaths" if "Total Deaths" in df.columns else next((c for c in df.columns if _norm(c) in ("totaldeaths","deaths","totaldeath")), None)
    affected_col = "Total Affected" if "Total Affected" in df.columns else next((c for c in df.columns if _norm(c) in ("totalaffected","affected")), None)

    dmg_col = _damage_adjusted_column(df)

    events: List[DisasterEvent] = []
    for i, row in df.iterrows():
        dmg = _to_float(row[dmg_col]) if dmg_col else None
        if dmg is not None and dmg_col and "'000" in dmg_col:
            dmg = dmg * 1000.0  # convert to US$

        events.append(DisasterEvent(
            event_id=i,
            dis_no=_to_str(row[dis_no_col]),
            country=_to_str(row[country_col]),
            disaster_type=_to_str(row[type_col]),
            disaster_subtype=_to_str(row[subtype_col]),
            start_year=int(row[sy_col]),
            start_month=_to_int(row[sm_col]) if sm_col else None,
            start_day=_to_int(row[sd_col]) if sd_col else None,
            end_year=_to_int(row[ey_col]) if ey_col else None,
            end_month=_to_int(row[em_col]) if em_col else None,
            end_day=_to_int(row[ed_col]) if ed_col else None,
            total_deaths=_to_int(row[deaths_col]) if deaths_col else None,
            total_affected=_to_int(row[affected_col]) if affected_col else None,
            total_damage_adj_usd=dmg,
        ))
    return events
