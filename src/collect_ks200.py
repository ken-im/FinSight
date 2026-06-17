"""KS200 최근 10년치 일별 시세를 수집하여 Neon DB에 적재한다.

실행: `uv run python -m src.collect_ks200`
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.collectors import fdr_collector
from src.db.database import engine, healthcheck
from src.db.models import DailyPrice
from src.init_db import PILOT_SYMBOL, create_tables, get_or_create_symbol
from src.loader import to_records, upsert_daily_prices

logger = logging.getLogger(__name__)


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

        records = to_records(df, symbol_id)
        count = upsert_daily_prices(
            session, records, symbol_id, PILOT_SYMBOL["symbol_nm"]
        )
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
