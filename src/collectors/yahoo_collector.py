"""yfinance 기반 일별 시세 수집기.

FDR가 지원하지 않거나 표기가 다른 종목(예: 닛케이 `^N225`, 금 선물 `GC=F`)을
Yahoo Finance에서 수집한다. `fdr_collector`와 동일한 출력 스키마를 따른다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

SOURCE = "YAHOO"

_TARGET_COLS = [
    "trade_dt",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
    "trade_amount",
    "change_rate",
]


def collect_daily_prices(symbol: str, start: str, end: str) -> pd.DataFrame:
    """단일 종목의 일별 시세를 수집해 정규화된 DataFrame으로 반환한다.

    fdr_collector와 동일한 컬럼(trade_dt, close_price, ...)을 반환하며,
    yfinance의 `end`는 미포함이므로 내부에서 +1일 보정해 `end`까지 포함한다.
    모든 결측치(NaN)는 DB 적재를 위해 None으로 변환된다.
    """
    end_inclusive = (
        datetime.strptime(end, "%Y-%m-%d").date() + timedelta(days=1)
    ).isoformat()

    logger.info("[%s] %s 시세 수집 시작 (%s ~ %s)", SOURCE, symbol, start, end)
    raw = yf.download(
        symbol,
        start=start,
        end=end_inclusive,
        progress=False,
        auto_adjust=False,
    )

    if raw is None or raw.empty:
        logger.warning("[%s] %s 수집 결과가 비어 있습니다.", SOURCE, symbol)
        return pd.DataFrame()

    df = raw.copy()
    # 단일 종목도 MultiIndex 컬럼으로 반환되는 경우가 있어 평탄화
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    out = pd.DataFrame()
    out["trade_dt"] = pd.to_datetime(df.index).strftime("%Y%m%d")
    out["open_price"] = df["Open"].to_numpy()
    out["high_price"] = df["High"].to_numpy()
    out["low_price"] = df["Low"].to_numpy()
    out["close_price"] = df["Close"].to_numpy()
    out["volume"] = df["Volume"].to_numpy()
    out["trade_amount"] = None  # Yahoo는 거래대금 미제공
    out["change_rate"] = df["Close"].pct_change().round(6).to_numpy()

    out = out[_TARGET_COLS].reset_index(drop=True)
    # NaN → None 변환 (DB Insert 전 필수, .cursorrules)
    out = out.replace({np.nan: None})

    logger.info("[%s] %s 수집 완료: %d건", SOURCE, symbol, len(out))
    return out
