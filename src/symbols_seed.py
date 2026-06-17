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

# PRD 2.1 수집 대상 종목 (source, symbol, symbol_nm, remark)
SYMBOLS: list[dict[str, str]] = [
    {"source": "FDR", "symbol": "KS11", "symbol_nm": "KOSPI 지수", "remark": "코스피 종합지수"},
    {"source": "FDR", "symbol": "KQ11", "symbol_nm": "KOSDAQ 지수", "remark": "코스닥 종합지수"},
    {"source": "FDR", "symbol": "KS200", "symbol_nm": "KOSPI 200", "remark": "코스피 200개 기업 지수"},
    {"source": "FDR", "symbol": "DJI", "symbol_nm": "다우존스 지수", "remark": "미국 우량주 30개 종목"},
    {"source": "FDR", "symbol": "IXIC", "symbol_nm": "나스닥 종합지수", "remark": "미국 기술주 중심"},
    {"source": "FDR", "symbol": "US500", "symbol_nm": "S&P 500 지수", "remark": "미국 대표 500개 기업"},
    {"source": "FDR", "symbol": "VIX", "symbol_nm": "공포 지수", "remark": "S&P 500 변동성 지수"},
    {"source": "YAHOO", "symbol": "^N225", "symbol_nm": "닛케이 225", "remark": "일본 대표 지수 (Yahoo: ^N225)"},
    {"source": "FDR", "symbol": "SSEC", "symbol_nm": "상해 종합지수", "remark": "중국 본토 시장"},
    {"source": "FDR", "symbol": "HSI", "symbol_nm": "항셍 지수", "remark": "홍콩 시장"},
    {"source": "YAHOO", "symbol": "GC=F", "symbol_nm": "금 선물", "remark": "금 선물 (Yahoo: GC=F)"},
    {"source": "FDR", "symbol": "CL", "symbol_nm": "WTI 선물", "remark": "WTI 선물"},
    {"source": "FDR", "symbol": "AAPL", "symbol_nm": "Apple", "remark": "애플 종가"},
    {"source": "FDR", "symbol": "005930", "symbol_nm": "삼성전자", "remark": "삼성전자 종가"},
    {"source": "FDR", "symbol": "BTC/USD", "symbol_nm": "비트코인/달러", "remark": "비트코인 달러 가격"},
    {"source": "FDR", "symbol": "ETH/USD", "symbol_nm": "이더리움/달러", "remark": "이더리움 달러 가격"},
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
