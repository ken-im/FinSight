"""daily_price 적재 공통 로직.

수집 진입점(`collect_ks200`, `collect`)이 공유한다.
로그는 본 모듈(`src.loader`) 이름으로 남으며, 적재 진행 시 symbol 정보를 함께 표시한다.
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.db.models import DailyPrice

logger = logging.getLogger(__name__)

# upsert 배치 크기 (대용량 대비 chunk 단위 처리)
BATCH_SIZE = 500

# 충돌 시 갱신할 컬럼
_UPDATE_COLS = [
    "close_price",
    "open_price",
    "high_price",
    "low_price",
    "volume",
    "trade_amount",
    "change_rate",
]


def to_records(df: pd.DataFrame, symbol_id: int) -> list[dict]:
    """정규화된 DataFrame을 daily_price 적재용 레코드 리스트로 변환한다.

    `close_price`가 없는(None) 일자는 적재 대상에서 제외한다(NOT NULL 컬럼).
    """
    records: list[dict] = []
    dropped = 0
    for row in df.to_dict(orient="records"):
        if row.get("close_price") is None:
            dropped += 1
            continue
        records.append({"symbol_id": symbol_id, **row})
    if dropped:
        logger.warning(
            "close_price 누락으로 %d건 제외 (symbol_id=%s)", dropped, symbol_id
        )
    return records


def upsert_daily_prices(
    session: Session,
    records: list[dict],
    symbol_id: int | None = None,
    symbol_nm: str | None = None,
) -> int:
    """(symbol_id, trade_dt) 충돌 시 갱신하는 멱등 upsert. 처리 건수를 반환한다.

    `symbol_id`/`symbol_nm`가 주어지면 적재 진행 로그에 함께 표시한다.
    """
    if not records:
        return 0

    label = ""
    if symbol_id is not None or symbol_nm is not None:
        label = f" [symbol_id={symbol_id}, {symbol_nm}]"

    total = 0
    for start in range(0, len(records), BATCH_SIZE):
        chunk = records[start : start + BATCH_SIZE]
        stmt = pg_insert(DailyPrice).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol_id", "trade_dt"],
            set_={col: getattr(stmt.excluded, col) for col in _UPDATE_COLS},
        )
        session.execute(stmt)
        total += len(chunk)
        logger.info("적재 진행%s: %d/%d", label, total, len(records))

    return total
