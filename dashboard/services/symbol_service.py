"""symbol_master 조회/CRUD 서비스.

- 중복 검증: `(source, symbol)` 유니크.
- 수정은 ORM 객체 방식으로 처리하여 `updated_at`(onupdate)이 갱신되도록 한다.
- 삭제는 종가내역(daily_price)이 있으면 가드(차단)한다.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dashboard.services.connection import get_engine
from src.db.models import DailyPrice, SymbolMaster

logger = logging.getLogger(__name__)


class DuplicateSymbolError(Exception):
    """(source, symbol) 중복."""


class DeleteBlockedError(Exception):
    """종가내역 존재로 삭제 불가."""


def _to_dict(row: SymbolMaster) -> dict:
    return {
        "symbol_id": row.symbol_id,
        "source": row.source,
        "symbol": row.symbol,
        "symbol_nm": row.symbol_nm,
        "remark": row.remark,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def list_symbols(
    symbol_id: int | None = None,
    source: str | None = None,
    symbol: str | None = None,
    symbol_nm: str | None = None,
) -> list[dict]:
    """필터(부분일치, symbol_id는 정확일치) 조회. symbol_id 오름차순."""
    with Session(get_engine()) as session:
        stmt = select(SymbolMaster).order_by(SymbolMaster.symbol_id)
        if symbol_id is not None:
            stmt = stmt.where(SymbolMaster.symbol_id == symbol_id)
        if source:
            stmt = stmt.where(SymbolMaster.source.ilike(f"%{source}%"))
        if symbol:
            stmt = stmt.where(SymbolMaster.symbol.ilike(f"%{symbol}%"))
        if symbol_nm:
            stmt = stmt.where(SymbolMaster.symbol_nm.ilike(f"%{symbol_nm}%"))
        return [_to_dict(r) for r in session.scalars(stmt)]


def get_symbol(symbol_id: int) -> dict | None:
    with Session(get_engine()) as session:
        row = session.get(SymbolMaster, symbol_id)
        return _to_dict(row) if row else None


def _exists_source_symbol(
    session: Session, source: str, symbol: str, exclude_id: int | None = None
) -> bool:
    stmt = select(SymbolMaster.symbol_id).where(
        SymbolMaster.source == source, SymbolMaster.symbol == symbol
    )
    if exclude_id is not None:
        stmt = stmt.where(SymbolMaster.symbol_id != exclude_id)
    return session.scalar(stmt) is not None


def create_symbol(source: str, symbol: str, symbol_nm: str, remark: str | None) -> int:
    """신규 등록. 중복 시 DuplicateSymbolError."""
    with Session(get_engine()) as session:
        if _exists_source_symbol(session, source, symbol):
            raise DuplicateSymbolError(f"이미 존재하는 종목입니다: {source}/{symbol}")
        row = SymbolMaster(source=source, symbol=symbol, symbol_nm=symbol_nm, remark=remark)
        session.add(row)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            logger.exception("종목 등록 중 무결성 오류")
            raise DuplicateSymbolError(f"이미 존재하는 종목입니다: {source}/{symbol}") from exc
        return row.symbol_id


def update_symbol(
    symbol_id: int, source: str, symbol: str, symbol_nm: str, remark: str | None
) -> None:
    """수정. ORM 객체 방식으로 updated_at(onupdate) 자동 갱신. 중복 시 DuplicateSymbolError."""
    with Session(get_engine()) as session:
        row = session.get(SymbolMaster, symbol_id)
        if row is None:
            raise ValueError(f"존재하지 않는 symbol_id: {symbol_id}")
        if _exists_source_symbol(session, source, symbol, exclude_id=symbol_id):
            raise DuplicateSymbolError(f"이미 존재하는 종목입니다: {source}/{symbol}")
        row.source = source
        row.symbol = symbol
        row.symbol_nm = symbol_nm
        row.remark = remark
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            logger.exception("종목 수정 중 무결성 오류")
            raise DuplicateSymbolError(f"이미 존재하는 종목입니다: {source}/{symbol}") from exc


def delete_symbol(symbol_id: int) -> None:
    """삭제. 종가내역이 있으면 DeleteBlockedError(가드 정책)."""
    with Session(get_engine()) as session:
        price_count = session.scalar(
            select(func.count())
            .select_from(DailyPrice)
            .where(DailyPrice.symbol_id == symbol_id)
        )
        if price_count:
            raise DeleteBlockedError(
                f"종가내역 {price_count}건이 존재하여 삭제할 수 없습니다."
            )
        row = session.get(SymbolMaster, symbol_id)
        if row is None:
            return
        session.delete(row)
        session.commit()
