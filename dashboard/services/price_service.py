"""daily_price query service.

Admin pages : count_prices, list_prices
Dashboard   : get_series, list_symbol_coverage
"""

from __future__ import annotations

import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dashboard.services.connection import get_engine
from src.db.models import DailyPrice, SymbolMaster

PAGE_SIZE = 30


# ── Admin pages ──────────────────────────────────────────────────────────

def count_prices(symbol_id: int) -> int:
    with Session(get_engine()) as session:
        return session.scalar(
            select(func.count())
            .select_from(DailyPrice)
            .where(DailyPrice.symbol_id == symbol_id)
        ) or 0


def list_prices(symbol_id: int, page: int = 1, page_size: int = PAGE_SIZE) -> list[dict]:
    """trade_dt DESC, page_size rows per page."""
    offset = max(0, (page - 1) * page_size)
    with Session(get_engine()) as session:
        stmt = (
            select(DailyPrice)
            .where(DailyPrice.symbol_id == symbol_id)
            .order_by(DailyPrice.trade_dt.desc())
            .limit(page_size)
            .offset(offset)
        )
        return [
            {
                "trade_dt":     r.trade_dt,
                "close_price":  r.close_price,
                "open_price":   r.open_price,
                "high_price":   r.high_price,
                "low_price":    r.low_price,
                "volume":       r.volume,
                "trade_amount": r.trade_amount,
                "change_rate":  r.change_rate,
            }
            for r in session.scalars(stmt)
        ]


# ── Dashboard ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_series(
    symbol_ids: tuple[int, ...], from_dt: str, to_dt: str
) -> list[dict]:
    """Multi-symbol close price for a date range.

    Args:
        symbol_ids: sorted tuple for consistent cache keys.
        from_dt / to_dt: YYYYMMDD strings (both inclusive).

    Returns:
        List of {symbol_id, trade_dt, close_price}.
    """
    if not symbol_ids:
        return []
    with Session(get_engine()) as session:
        stmt = (
            select(
                DailyPrice.symbol_id,
                DailyPrice.trade_dt,
                DailyPrice.close_price,
            )
            .where(
                DailyPrice.symbol_id.in_(list(symbol_ids)),
                DailyPrice.trade_dt >= from_dt,
                DailyPrice.trade_dt <= to_dt,
            )
            .order_by(DailyPrice.trade_dt, DailyPrice.symbol_id)
        )
        return [
            {
                "symbol_id":   r.symbol_id,
                "trade_dt":    r.trade_dt,
                "close_price": float(r.close_price),
            }
            for r in session.execute(stmt)
        ]


def list_daily_prices(
    symbol_id: int,
    from_dt: str,
    to_dt: str,
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> tuple[list[dict], int]:
    """Daily prices within date range with pagination.

    Returns:
        (rows, total_count) where rows are trade_dt DESC.
    """
    with Session(get_engine()) as session:
        base = (
            select(DailyPrice)
            .where(
                DailyPrice.symbol_id == symbol_id,
                DailyPrice.trade_dt >= from_dt,
                DailyPrice.trade_dt <= to_dt,
            )
        )
        total = session.scalar(
            select(func.count()).select_from(base.subquery())
        ) or 0

        offset = max(0, (page - 1) * page_size)
        stmt = base.order_by(DailyPrice.trade_dt.desc()).limit(page_size).offset(offset)
        rows = [
            {
                "trade_dt":     r.trade_dt,
                "close_price":  r.close_price,
                "open_price":   r.open_price,
                "high_price":   r.high_price,
                "low_price":    r.low_price,
                "volume":       r.volume,
                "trade_amount": r.trade_amount,
                "change_rate":  r.change_rate,
            }
            for r in session.scalars(stmt)
        ]
    return rows, total


@st.cache_data(ttl=3600, show_spinner=False)
def list_symbol_coverage() -> list[dict]:
    """Per-symbol data coverage (MIN/MAX trade_dt and row count).

    Returns:
        List of {symbol_id, symbol_nm, from_dt, to_dt, cnt}.
    """
    with Session(get_engine()) as session:
        stmt = (
            select(
                SymbolMaster.symbol_id,
                SymbolMaster.symbol_nm,
                func.min(DailyPrice.trade_dt).label("from_dt"),
                func.max(DailyPrice.trade_dt).label("to_dt"),
                func.count().label("cnt"),
            )
            .join(DailyPrice, SymbolMaster.symbol_id == DailyPrice.symbol_id)
            .group_by(SymbolMaster.symbol_id, SymbolMaster.symbol_nm)
            .order_by(SymbolMaster.symbol_id)
        )
        return [
            {
                "symbol_id": r.symbol_id,
                "symbol_nm": r.symbol_nm,
                "from_dt":   r.from_dt,
                "to_dt":     r.to_dt,
                "cnt":       r.cnt,
            }
            for r in session.execute(stmt)
        ]
