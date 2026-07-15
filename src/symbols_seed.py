"""종목마스터(symbol_master) 전체 시드(seed) 등록.

PRD 2.1의 수집 대상 종목을 `(source, symbol)` 기준으로 멱등 등록한다.
실행: `uv run python -m src.symbols_seed`
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.db.database import engine, healthcheck
from src.init_db import create_tables, get_or_create_symbol

logger = logging.getLogger(__name__)

# PRD 2.1 수집 대상 종목 (source, symbol, symbol_nm, remark, data_frequency, category)
SYMBOLS: list[dict[str, str | None]] = [
    # ── 기존 시장지표 (16종) ──
    {"source": "FDR", "symbol": "KS11", "symbol_nm": "KOSPI 지수", "remark": "코스피 종합지수", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "KQ11", "symbol_nm": "KOSDAQ 지수", "remark": "코스닥 종합지수", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "KS200", "symbol_nm": "KOSPI 200", "remark": "코스피 200개 기업 지수", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "DJI", "symbol_nm": "다우존스 지수", "remark": "미국 우량주 30개 종목", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "IXIC", "symbol_nm": "나스닥 종합지수", "remark": "미국 기술주 중심", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "US500", "symbol_nm": "S&P 500 지수", "remark": "미국 대표 500개 기업", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "VIX", "symbol_nm": "공포 지수", "remark": "S&P 500 변동성 지수", "data_frequency": "Daily", "category": "Market"},
    {"source": "YAHOO", "symbol": "^N225", "symbol_nm": "닛케이 225", "remark": "일본 대표 지수 (Yahoo: ^N225)", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "SSEC", "symbol_nm": "상해 종합지수", "remark": "중국 본토 시장", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "HSI", "symbol_nm": "항셍 지수", "remark": "홍콩 시장", "data_frequency": "Daily", "category": "Market"},
    {"source": "YAHOO", "symbol": "GC=F", "symbol_nm": "금 선물", "remark": "금 선물 (Yahoo: GC=F)", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "CL", "symbol_nm": "WTI 선물", "remark": "WTI 선물", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "AAPL", "symbol_nm": "Apple", "remark": "애플 종가", "data_frequency": "Daily", "category": "Stock"},
    {"source": "FDR", "symbol": "005930", "symbol_nm": "삼성전자", "remark": "삼성전자 종가", "data_frequency": "Daily", "category": "Stock"},
    {"source": "FDR", "symbol": "BTC/USD", "symbol_nm": "비트코인/달러", "remark": "비트코인 달러 가격", "data_frequency": "Daily", "category": "Market"},
    {"source": "FDR", "symbol": "ETH/USD", "symbol_nm": "이더리움/달러", "remark": "이더리움 달러 가격", "data_frequency": "Daily", "category": "Market"},
    # ── FRED 경제지표 (10종) ──
    {"source": "FRED", "symbol": "FEDFUNDS", "symbol_nm": "Fed 기준금리", "remark": "Effective Federal Funds Rate", "data_frequency": "Monthly", "category": "FRED"},
    {"source": "FRED", "symbol": "T10Y3M", "symbol_nm": "장단기금리차", "remark": "10-Year Minus 3-Month Treasury", "data_frequency": "Daily", "category": "FRED"},
    {"source": "FRED", "symbol": "PPIACO", "symbol_nm": "생산자물가지수(PPI)", "remark": "Producer Price Index: All Commodities", "data_frequency": "Monthly", "category": "FRED"},
    {"source": "FRED", "symbol": "CPIAUCSL", "symbol_nm": "소비자물가지수(CPI)", "remark": "Consumer Price Index for All Urban Consumers", "data_frequency": "Monthly", "category": "FRED"},
    {"source": "FRED", "symbol": "DFII10", "symbol_nm": "미국채10년물", "remark": "10-Year Treasury Yield", "data_frequency": "Daily", "category": "FRED"},
    {"source": "FRED", "symbol": "DGS3MO", "symbol_nm": "미국채3개월물", "remark": "3-Month Treasury Yield", "data_frequency": "Daily", "category": "FRED"},
    {"source": "FRED", "symbol": "UNRATE", "symbol_nm": "실업률", "remark": "Unemployment Rate", "data_frequency": "Monthly", "category": "FRED"},
    {"source": "FRED", "symbol": "NFCI", "symbol_nm": "금융상황지수", "remark": "Chicago Fed National Financial Conditions Index", "data_frequency": "Weekly", "category": "FRED"},
    {"source": "FRED", "symbol": "HOUST", "symbol_nm": "신규주택착공", "remark": "New Privately-Owned Housing Units Started", "data_frequency": "Monthly", "category": "FRED"},
    {"source": "FRED", "symbol": "USREC", "symbol_nm": "경기침체구간", "remark": "NBER Recession Indicators (1=침체)", "data_frequency": "Monthly", "category": "FRED"},
]


def seed_symbols(session: Session) -> list[int]:
    """종목마스터에 전체 종목을 멱등 등록하고 symbol_id 목록을 반환한다."""
    symbol_ids: list[int] = []
    for item in SYMBOLS:
        symbol_ids.append(get_or_create_symbol(session, **item))
    return symbol_ids


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    if not healthcheck():
        raise SystemExit("DB 접속에 실패하여 시드를 중단합니다.")

    create_tables()
    with Session(engine) as session:
        symbol_ids = seed_symbols(session)
        session.commit()
    logger.info("종목마스터 시드 완료: 총 %d종", len(symbol_ids))


if __name__ == "__main__":
    main()
