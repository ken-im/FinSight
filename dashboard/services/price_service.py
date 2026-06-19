"""daily_price 페이징 조회 서비스."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dashboard.services.connection import get_engine
from src.db.models import DailyPrice

PAGE_SIZE = 20


def count_prices(symbol_id: int) -> int:
    with Session(get_engine()) as session:
        return session.scalar(
            select(func.count())
            .select_from(DailyPrice)
            .where(DailyPrice.symbol_id == symbol_id)
        ) or 0


def list_prices(symbol_id: int, page: int = 1, page_size: int = PAGE_SIZE) -> list[dict]:
    """trade_dt DESC, 페이지당 page_size행."""
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
                "trade_dt": r.trade_dt,
                "close_price": r.close_price,
                "open_price": r.open_price,
                "high_price": r.high_price,
                "low_price": r.low_price,
                "volume": r.volume,
                "trade_amount": r.trade_amount,
                "change_rate": r.change_rate,
            }
            for r in session.scalars(stmt)
        ]
