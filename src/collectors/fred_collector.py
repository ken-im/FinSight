"""FRED 경제지표 수집기 (FinanceDataReader 경유).

FinanceDataReader의 FRED 지원 기능을 활용하여
미연방준비은행(FRED) 경제지표를 수집한다.
FRED 데이터는 단일 값(Close)만 반환하며 OHLCV는 없다.

수집기 공통 인터페이스: collect_daily_prices(symbol, start, end) -> DataFrame
"""

from __future__ import annotations

import logging

import FinanceDataReader as fdr
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SOURCE = "FRED"

_TARGET_COLS = [
    "trade_dt",
    "close_price",
    "open_price",
    "high_price",
    "low_price",
    "volume",
    "trade_amount",
    "change_rate",
]


def collect_daily_prices(
    symbol: str, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    """FRED 경제지표를 수집해 daily_price 적재용 DataFrame으로 반환한다.

    FDR 호출 시 'FRED:{symbol}' 형태로 조합한다.
    반환 컬럼: trade_dt(YYYYMMDD), close_price (나머지 OHLCV는 None).
    모든 결측치(NaN)는 DB 적재를 위해 None으로 변환된다.
    """
    fdr_symbol = f"FRED:{symbol}"
    logger.info("[%s] %s 수집 시작 (%s ~ %s)", SOURCE, fdr_symbol, start, end)

    raw = fdr.DataReader(fdr_symbol, start, end)

    if raw is None or raw.empty:
        logger.warning("[%s] %s 수집 결과가 비어 있습니다.", SOURCE, fdr_symbol)
        return pd.DataFrame()

    out = pd.DataFrame()
    out["trade_dt"] = pd.to_datetime(raw.index).strftime("%Y%m%d")

    close_col = "Close" if "Close" in raw.columns else raw.columns[0]
    out["close_price"] = raw[close_col].to_numpy()

    out["open_price"] = None
    out["high_price"] = None
    out["low_price"] = None
    out["volume"] = None
    out["trade_amount"] = None
    out["change_rate"] = None

    out = out[_TARGET_COLS].reset_index(drop=True)
    out = out.replace({np.nan: None})

    logger.info("[%s] %s 수집 완료: %d건", SOURCE, fdr_symbol, len(out))
    return out
