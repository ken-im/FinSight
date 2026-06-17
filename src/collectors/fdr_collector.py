"""FinanceDataReader 기반 일별 시세 수집기.

파일럿에서는 FDR 원천 1종만 사용하지만, 추후 원천 추가(YAHOO 등)에 대비해
`source` 식별자와 수집 함수 구조를 분리해 둔다.
"""

from __future__ import annotations

import logging
from datetime import date

import FinanceDataReader as fdr
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SOURCE = "FDR"

# FDR 원본 컬럼 → 모델(daily_price) 컬럼 매핑
_COLUMN_MAP: dict[str, str] = {
    "Open": "open_price",
    "High": "high_price",
    "Low": "low_price",
    "Close": "close_price",
    "Volume": "volume",
    "Amount": "trade_amount",
    "Change": "change_rate",
}


def default_period(years: int = 10) -> tuple[str, str]:
    """수집 기간(start, end)을 `YYYY-MM-DD` 문자열로 반환한다. (기본 최근 10년)

    timedelta 방식은 윤년을 고려하지 않아 실제보다 짧은 기간이 산출되므로
    date.replace()로 정확히 N년을 뺀다. (2/29 → 2/28 자동 보정)
    """
    end = date.today()
    try:
        start = end.replace(year=end.year - years)
    except ValueError:
        start = end.replace(year=end.year - years, day=28)
    return start.isoformat(), end.isoformat()


def collect_daily_prices(
    symbol: str, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    """단일 종목의 일별 시세를 수집해 정규화된 DataFrame으로 반환한다.

    반환 컬럼: trade_dt(YYYYMMDD), close_price, open_price, high_price,
              low_price, volume, trade_amount, change_rate
    모든 결측치(NaN)는 DB 적재를 위해 None으로 변환된다.
    """
    if start is None or end is None:
        start, end = default_period()

    logger.info("[%s] %s 시세 수집 시작 (%s ~ %s)", SOURCE, symbol, start, end)
    raw = fdr.DataReader(symbol, start, end)

    if raw is None or raw.empty:
        logger.warning("[%s] %s 수집 결과가 비어 있습니다.", SOURCE, symbol)
        return pd.DataFrame()

    df = raw.rename(columns=_COLUMN_MAP).copy()

    # 일자 인덱스 → YYYYMMDD 문자열 컬럼
    df["trade_dt"] = pd.to_datetime(df.index).strftime("%Y%m%d")

    # 모델이 사용하는 컬럼만 유지 (원천에 없는 컬럼은 None으로 보강)
    target_cols = ["trade_dt", *(_COLUMN_MAP.values())]
    for col in target_cols:
        if col not in df.columns:
            df[col] = None
    df = df[target_cols].reset_index(drop=True)

    # NaN → None 변환 (DB Insert 전 필수, .cursorrules)
    df = df.replace({np.nan: None})

    logger.info("[%s] %s 수집 완료: %d건", SOURCE, symbol, len(df))
    return df
