"""Data transform: trade_dt->datetime, wide pivot, ffill, normalize."""

from __future__ import annotations

import pandas as pd


def to_wide(rows: list[dict], symbol_id_to_nm: dict[int, str]) -> pd.DataFrame:
    """Convert long rows -> wide DataFrame with ffill gap smoothing."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["trade_dt"]    = pd.to_datetime(df["trade_dt"], format="%Y%m%d")
    df["symbol_nm"]   = df["symbol_id"].map(symbol_id_to_nm)
    df["close_price"] = df["close_price"].astype(float)
    wide = df.pivot_table(
        index="trade_dt", columns="symbol_nm",
        values="close_price", aggfunc="first",
    )
    wide.columns.name = None
    return wide.sort_index().ffill()


def calc_sma(
    df: pd.DataFrame,
    close_col: str,
    windows: dict[str, int],
) -> pd.DataFrame:
    """Calculate Simple Moving Averages and append as new columns.

    Args:
        df: DatetimeIndex, must contain *close_col*.
        close_col: column name for close price.
        windows: ``{"MA3M": 60, "MA1Y": 250, ...}`` label -> window size.

    Returns:
        Copy of *df* with MA columns appended.
    """
    result = df.copy()
    for label, w in windows.items():
        result[label] = result[close_col].rolling(window=w, min_periods=w).mean()
    return result


def normalize_100(wide: pd.DataFrame) -> pd.DataFrame:
    """Normalize each column: first valid value = 100."""
    if wide.empty:
        return wide
    result = wide.copy()
    for col in result.columns:
        idx = result[col].first_valid_index()
        if idx is None:
            continue
        base = result.loc[idx, col]
        if base and base != 0:
            result[col] = result[col] / base * 100.0
    return result
