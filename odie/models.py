"""
Data model (DisasterEvent)
=========================

Each row in the EM-DAT Excel file is converted into a `DisasterEvent` object.
We keep it immutable (`frozen=True`) so that:
- events cannot be accidentally modified after loading, and
- filters/sorts operate by selecting IDs rather than editing data.

This matches the project's goal: *offline analysis of a non-updating dataset*.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class DisasterEvent:
    """One disaster event record.

    Fields are a curated subset of the Excel columns.
    ODIE can be extended to carry more columns later.
    """
    """Immutable record for one EM-DAT row."""
    event_id: int
    dis_no: str
    country: str
    disaster_type: str
    disaster_subtype: str
    start_year: int
    start_month: Optional[int]
    start_day: Optional[int]
    end_year: Optional[int]
    end_month: Optional[int]
    end_day: Optional[int]
    total_deaths: Optional[int]
    total_affected: Optional[int]
    # stored in US$ (not '000)
    total_damage_adj_usd: Optional[float]

    def start_date_key(self) -> int:
        """Return an integer YYYYMMDD key for sorting by start date."""
        m = self.start_month or 1
        d = self.start_day or 1
        return self.start_year * 10000 + m * 100 + d
