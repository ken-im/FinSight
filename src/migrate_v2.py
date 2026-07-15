"""symbol_master 스키마 확장 마이그레이션.

data_frequency, category 컬럼 추가 및 기존 데이터 보정.
IF NOT EXISTS 사용으로 멱등 실행 가능.

실행: uv run python -m src.migrate_v2
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.db.database import engine, healthcheck

logger = logging.getLogger(__name__)

_STOCK_SYMBOLS = ("AAPL", "005930")

_ALTER_STATEMENTS = [
    "ALTER TABLE symbol_master ADD COLUMN IF NOT EXISTS data_frequency VARCHAR(20);",
    "ALTER TABLE symbol_master ADD COLUMN IF NOT EXISTS category VARCHAR(20);",
]

_UPDATE_STATEMENTS = [
    "UPDATE symbol_master SET data_frequency = 'Daily' WHERE data_frequency IS NULL;",
    "UPDATE symbol_master SET category = 'Stock' WHERE symbol IN :stock_symbols AND category IS NULL;",
    "UPDATE symbol_master SET category = 'Market' WHERE source IN ('FDR', 'YAHOO') AND category IS NULL;",
]


def migrate(session: Session) -> None:
    """ALTER TABLE + 기존 데이터 보정."""
    for stmt in _ALTER_STATEMENTS:
        session.execute(text(stmt))
        logger.info("DDL: %s", stmt.strip())
    session.commit()

    r1 = session.execute(
        text("UPDATE symbol_master SET data_frequency = 'Daily' WHERE data_frequency IS NULL;")
    )
    logger.info("data_frequency='Daily' 설정: %d건", r1.rowcount)

    r2 = session.execute(
        text("UPDATE symbol_master SET category = 'Stock' WHERE symbol = ANY(:syms) AND category IS NULL;"),
        {"syms": list(_STOCK_SYMBOLS)},
    )
    logger.info("category='Stock' 설정: %d건", r2.rowcount)

    r3 = session.execute(
        text("UPDATE symbol_master SET category = 'Market' WHERE source = ANY(:sources) AND category IS NULL;"),
        {"sources": ["FDR", "YAHOO"]},
    )
    logger.info("category='Market' 설정: %d건", r3.rowcount)

    session.commit()
    logger.info("기존 데이터 보정 완료")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    if not healthcheck():
        raise SystemExit("DB 접속에 실패하여 마이그레이션을 중단합니다.")

    with Session(engine) as session:
        migrate(session)

    logger.info("마이그레이션 v2 완료.")


if __name__ == "__main__":
    main()
