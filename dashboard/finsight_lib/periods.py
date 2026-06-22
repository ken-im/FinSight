"""Period preset -> from_date calculation (calendar-based, no dateutil)."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

PRESETS: list[str] = [
    "1주",
    "1개월",
    "3개월",
    "6개월",
    "1년",
    "3년",
    "10년",
    "직접지정",
]
DEFAULT_PRESET: str = "1년"
DIRECT_LABEL:   str = "직접지정"


def from_date_by_preset(to_date: date, preset: str) -> date:
    if preset == "1주":
        return to_date - timedelta(days=7)
    if preset == "1개월":
        return _subtract_months(to_date, 1)
    if preset == "3개월":
        return _subtract_months(to_date, 3)
    if preset == "6개월":
        return _subtract_months(to_date, 6)
    if preset == "1년":
        return _subtract_years(to_date, 1)
    if preset == "3년":
        return _subtract_years(to_date, 3)
    if preset == "10년":
        return _subtract_years(to_date, 10)
    return to_date


def _subtract_months(d: date, months: int) -> date:
    total = d.year * 12 + (d.month - 1) - months
    year, rem = divmod(total, 12)
    month = rem + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def _subtract_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return d.replace(year=d.year - years, day=28)
