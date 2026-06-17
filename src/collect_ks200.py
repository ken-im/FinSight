"""KS200 최근 10년치 일별 시세를 수집하여 Neon DB에 적재한다.

실행: `uv run python -m src.collect_ks200`
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.collectors import fdr_collector
from src.db.database import engine, healthcheck
from src.db.models import DailyPrice
from src.init_db import PILOT_SYMBOL, create_tables, get_or_create_symbol

logger = logging.getLogger(__name__)

# upsert 배치 크기 (대용량 대비 chunk 단위 처리)
BATCH_SIZE = 500


def _to_records(df: pd.DataFrame, symbol_id: int) -> list[dict]:
    """정규화된 DataFrame을 daily_price 적재용 레코드 리스트로 변환한다."""
    records: list[dict] = []
    for row in df.to_dict(orient="records"):
        record = {"symbol_id": symbol_id, **row}
        records.append(record)
    return records


def upsert_daily_prices(session: Session, records: list[dict]) -> int:
    """(symbol_id, trade_dt) 충돌 시 갱신하는 멱등 upsert. 처리 건수를 반환한다."""
    if not records:
        return 0

    update_cols = [
        "close_price",
        "open_price",
        "high_price",
        "low_price",
        "volume",
        "trade_amount",
        "change_rate",
    ]

    total = 0
    for start in range(0, len(records), BATCH_SIZE):
        chunk = records[start : start + BATCH_SIZE]
        stmt = pg_insert(DailyPrice).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol_id", "trade_dt"],
            set_={col: getattr(stmt.excluded, col) for col in update_cols},
        )
        session.execute(stmt)
        total += len(chunk)
        logger.info("적재 진행: %d/%d", total, len(records))

    return total


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    if not healthcheck():
        raise SystemExit("DB 접속에 실패하여 수집을 중단합니다.")

    create_tables()

    with Session(engine) as session:
        symbol_id = get_or_create_symbol(session, **PILOT_SYMBOL)

        df = fdr_collector.collect_daily_prices(PILOT_SYMBOL["symbol"])
        if df.empty:
            session.commit()
            raise SystemExit("수집된 데이터가 없어 적재를 중단합니다.")

        records = _to_records(df, symbol_id)
        count = upsert_daily_prices(session, records)
        session.commit()

        # 검증용 집계
        total = session.scalar(
            select(func.count())
            .select_from(DailyPrice)
            .where(DailyPrice.symbol_id == symbol_id)
        )
        min_dt = session.scalar(
            select(func.min(DailyPrice.trade_dt)).where(
                DailyPrice.symbol_id == symbol_id
            )
        )
        max_dt = session.scalar(
            select(func.max(DailyPrice.trade_dt)).where(
                DailyPrice.symbol_id == symbol_id
            )
        )

    logger.info("적재 완료: %d건 처리 / 누적 %d건 (%s ~ %s)", count, total, min_dt, max_dt)


if __name__ == "__main__":
    main()
