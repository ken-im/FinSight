"""범용 일괄 수집·적재 배치 진입점.

종목마스터의 대상 종목을 일괄 수집하여 Neon DB에 적재한다.

실행 예시:
  uv run python -m src.collect
  uv run python -m src.collect --to-date 20260617
  uv run python -m src.collect --from-date 20260101 --to-date 20260617
  uv run python -m src.collect --symbol-id 3 --from-date 20160101 --to-date 20260617
"""

from __future__ import annotations

import argparse
import calendar
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.collectors import fdr_collector, yahoo_collector
from src.db.database import engine, healthcheck
from src.db.models import SymbolMaster
from src.init_db import create_tables
from src.loader import to_records, upsert_daily_prices
from src.logging_config import append_trailing_blank_lines, setup_logging

logger = logging.getLogger(__name__)

DATE_FMT = "%Y%m%d"

# source → 수집 함수 매핑 (공통 인터페이스: fn(symbol, start_iso, end_iso) -> DataFrame)
_COLLECTORS: dict[str, Callable[[str, str, str], pd.DataFrame]] = {
    "FDR": fdr_collector.collect_daily_prices,
    "YAHOO": yahoo_collector.collect_daily_prices,
}


@dataclass
class SymbolTarget:
    symbol_id: int
    source: str
    symbol: str
    symbol_nm: str


@dataclass
class CollectResult:
    symbol_id: int
    symbol_nm: str
    from_dt: str
    to_dt: str
    count: int
    status: str


def _parse_yyyymmdd(value: str) -> date:
    try:
        return datetime.strptime(value, DATE_FMT).date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"날짜 형식이 올바르지 않습니다(yyyymmdd): {value!r}"
        ) from exc


def minus_one_month(d: date) -> date:
    """달력 기준 1개월 전 날짜를 반환한다(말일 보정 포함)."""
    year, month = (d.year, d.month - 1)
    if month == 0:
        year, month = year - 1, 12
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(d.day, last_day))


def parse_args(argv: list[str] | None = None) -> tuple[date, date, int | None]:
    parser = argparse.ArgumentParser(description="FinSight 일괄 수집·적재 배치")
    parser.add_argument(
        "--to-date", type=_parse_yyyymmdd, default=None,
        help="수집 종료일(yyyymmdd, 생략 시 현재일자)",
    )
    parser.add_argument(
        "--from-date", type=_parse_yyyymmdd, default=None,
        help="수집 시작일(yyyymmdd, 생략 시 to일자 1개월 전)",
    )
    parser.add_argument(
        "--symbol-id", type=int, default=None,
        help="특정 종목만 수집(생략 시 전체 대상)",
    )
    args = parser.parse_args(argv)

    to_date = args.to_date or date.today()
    from_date = args.from_date or minus_one_month(to_date)
    if from_date > to_date:
        parser.error(f"from일자({from_date})가 to일자({to_date})보다 큽니다.")
    return to_date, from_date, args.symbol_id


def resolve_targets(session: Session, symbol_id: int | None) -> list[SymbolTarget]:
    stmt = select(SymbolMaster).order_by(SymbolMaster.symbol_id)
    if symbol_id is not None:
        stmt = stmt.where(SymbolMaster.symbol_id == symbol_id)
    return [
        SymbolTarget(s.symbol_id, s.source, s.symbol, s.symbol_nm)
        for s in session.scalars(stmt)
    ]


def _log_summary(results: list[CollectResult], to_str: str) -> None:
    total = sum(r.count for r in results)
    fail = sum(1 for r in results if r.status != "OK")
    lines = [
        f"======== 수집 요약 (to일자: {to_str}) ========",
        f"{'symbol_id':>9}  {'명칭':<14} {'from':<10} {'to':<10} {'총건수':>8}  상태",
    ]
    for r in results:
        lines.append(
            f"{r.symbol_id:>9}  {r.symbol_nm:<14} {r.from_dt:<10} {r.to_dt:<10} {r.count:>8}  {r.status}"
        )
    lines.append("-" * 56)
    lines.append(
        f"대상 {len(results)}종목 / 적재 합계 {total}건 / 실패 {fail}종목"
    )
    lines.append("=" * 56)
    logger.info("수집 요약\n%s", "\n".join(lines))


def run(to_date: date, from_date: date, symbol_id: int | None) -> None:
    to_str = to_date.strftime(DATE_FMT)
    from_str = from_date.strftime(DATE_FMT)
    log_path = setup_logging(to_str)

    logger.info(
        "배치 시작: from=%s, to=%s, symbol_id=%s", from_str, to_str, symbol_id or "전체"
    )
    logger.info("로그 파일: %s", log_path)

    if not healthcheck():
        raise SystemExit("DB 접속에 실패하여 배치를 중단합니다.")
    create_tables()

    start_iso, end_iso = from_date.isoformat(), to_date.isoformat()
    results: dict[int, CollectResult] = {}

    with Session(engine) as session:
        targets = resolve_targets(session, symbol_id)
        if not targets:
            logger.warning(
                "대상 종목이 없습니다. 먼저 시드를 등록하세요: uv run python -m src.symbols_seed"
            )
            return

        def result(t: SymbolTarget, count: int, status: str) -> CollectResult:
            return CollectResult(t.symbol_id, t.symbol_nm, from_str, to_str, count, status)

        # ── 1단계: 일괄 수집 (DB 미접근) ───────────────────────────
        # 모든 종목을 먼저 수집하고, 성공한 종목만 메모리에 모은다.
        logger.info("[1/2] 일괄 수집 시작: 대상 %d종", len(targets))
        collected: list[tuple[SymbolTarget, pd.DataFrame]] = []
        for t in targets:
            collector = _COLLECTORS.get(t.source.upper())
            if collector is None:
                logger.error("[%s] %s 미지원 source — 건너뜁니다.", t.source, t.symbol)
                results[t.symbol_id] = result(t, 0, "SKIP")
                continue
            try:
                df = collector(t.symbol, start_iso, end_iso)
                collected.append((t, df))
            except Exception:
                logger.exception("[%s] %s 수집 실패", t.source, t.symbol)
                results[t.symbol_id] = result(t, 0, "FAIL_COLLECT")

        # ── 2단계: 수집 성공 종목만 일괄 적재 ──────────────────────
        # 종목별 savepoint로 격리한 뒤, 마지막에 한 번 커밋한다.
        logger.info("[2/2] 일괄 적재 시작: 수집 성공 %d종", len(collected))
        for t, df in collected:
            try:
                count = 0
                if not df.empty:
                    with session.begin_nested():
                        count = upsert_daily_prices(
                            session, to_records(df, t.symbol_id), t.symbol_id, t.symbol_nm
                        )
                results[t.symbol_id] = result(t, count, "OK")
            except Exception:
                logger.exception("[%s] %s 적재 실패", t.source, t.symbol)
                results[t.symbol_id] = result(t, 0, "FAIL_LOAD")
        session.commit()

    # 대상 순서대로 요약 정렬
    _log_summary([results[t.symbol_id] for t in targets], to_str)

    # 로그 파일 끝에 공백 라인 5개 추가 (실행 구분용)
    append_trailing_blank_lines(5)


def main(argv: list[str] | None = None) -> None:
    to_date, from_date, symbol_id = parse_args(argv)
    run(to_date, from_date, symbol_id)


if __name__ == "__main__":
    main()
