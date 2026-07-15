"""테이블 생성 및 종목마스터 초기 등록.

실행: `uv run python -m src.init_db`
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.database import engine, healthcheck
from src.db.models import Base, SymbolMaster

logger = logging.getLogger(__name__)

# 파일럿 대상 종목
PILOT_SYMBOL: dict[str, str] = {
    "source": "FDR",
    "symbol": "KS200",
    "symbol_nm": "KOSPI 200",
    "remark": "코스피 200개 기업 지수",
}


def create_tables() -> None:
    """ORM 메타데이터 기준으로 테이블을 생성한다(존재 시 무시)."""
    Base.metadata.create_all(engine)
    logger.info("테이블 생성/확인 완료: %s", ", ".join(Base.metadata.tables.keys()))


def get_or_create_symbol(
    session: Session,
    source: str,
    symbol: str,
    symbol_nm: str,
    remark: str | None = None,
    data_frequency: str | None = None,
    category: str | None = None,
) -> int:
    """(source, symbol)로 종목마스터를 조회하고 없으면 등록 후 symbol_id를 반환한다."""
    stmt = select(SymbolMaster).where(
        SymbolMaster.source == source, SymbolMaster.symbol == symbol
    )
    row = session.scalar(stmt)
    if row is not None:
        logger.info("기존 종목 사용: %s/%s (symbol_id=%d)", source, symbol, row.symbol_id)
        return row.symbol_id

    row = SymbolMaster(
        source=source, symbol=symbol, symbol_nm=symbol_nm, remark=remark,
        data_frequency=data_frequency, category=category,
    )
    session.add(row)
    session.flush()
    logger.info("신규 종목 등록: %s/%s (symbol_id=%d)", source, symbol, row.symbol_id)
    return row.symbol_id


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    if not healthcheck():
        raise SystemExit("DB 접속에 실패하여 초기화를 중단합니다.")

    create_tables()
    with Session(engine) as session:
        symbol_id = get_or_create_symbol(session, **PILOT_SYMBOL)
        session.commit()
    logger.info("초기화 완료. KS200 symbol_id=%d", symbol_id)


if __name__ == "__main__":
    main()
