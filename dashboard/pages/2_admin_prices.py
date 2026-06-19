"""관리자 — 종목종가내역 조회 (PRD 7.2)."""

# --- sys.path 부트스트랩 (다른 import보다 먼저) ---
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --------------------------------------------------

import math

import pandas as pd
import streamlit as st

from dashboard.services.auth import require_admin
from dashboard.services.price_service import PAGE_SIZE, count_prices, list_prices
from dashboard.services.symbol_service import list_symbols

st.set_page_config(page_title="종가내역 조회", page_icon="📊", layout="wide")
require_admin()

st.header("📊 종목종가내역")

symbols = list_symbols()
if not symbols:
    st.info("등록된 종목이 없습니다. 먼저 종목마스터에서 종목을 등록하세요.")
    st.stop()

# ── 종목 선택 (A안: 페이지에서 직접 선택, session_state 연동) ──
options = {
    f'{s["symbol_id"]} - {s["source"]}/{s["symbol"]} ({s["symbol_nm"]})': s["symbol_id"]
    for s in symbols
}
labels = list(options.keys())
ids = list(options.values())

default_id = st.session_state.get("selected_symbol_id")
default_index = ids.index(default_id) if default_id in ids else 0

chosen_label = st.selectbox("종목 선택", labels, index=default_index)
chosen_id = options[chosen_label]

if chosen_id != st.session_state.get("selected_symbol_id"):
    st.session_state["selected_symbol_id"] = chosen_id
    st.session_state["price_page"] = 1

# ── 페이징 계산 ──────────────────────────────────────
total = count_prices(chosen_id)
total_pages = max(1, math.ceil(total / PAGE_SIZE))
page = min(max(1, st.session_state.get("price_page", 1)), total_pages)
st.session_state["price_page"] = page

# ── 페이지 네비게이션 (<< 처음 / ◀ 이전 / 다음 ▶ / 마지막 >>) ──
c_first, c_prev, c_info, c_next, c_last = st.columns([1, 1, 3, 1, 1])
if c_first.button("<<", use_container_width=True, disabled=page <= 1, help="첫 페이지"):
    st.session_state["price_page"] = 1
    st.rerun()
if c_prev.button("◀", use_container_width=True, disabled=page <= 1, help="이전 페이지"):
    st.session_state["price_page"] = page - 1
    st.rerun()
c_info.markdown(
    f"<div style='text-align:center'>페이지 <b>{page}</b> / {total_pages} · 총 <b>{total}</b>건</div>",
    unsafe_allow_html=True,
)
if c_next.button("▶", use_container_width=True, disabled=page >= total_pages, help="다음 페이지"):
    st.session_state["price_page"] = page + 1
    st.rerun()
if c_last.button(">>", use_container_width=True, disabled=page >= total_pages, help="마지막 페이지"):
    st.session_state["price_page"] = total_pages
    st.rerun()

# ── 종가내역 표 (일자 DESC) ──────────────────────────
NUMERIC_COLS = [
    "close_price",
    "open_price",
    "high_price",
    "low_price",
    "volume",
    "trade_amount",
    "change_rate",
]


records = list_prices(chosen_id, page=page)
if records:
    df = pd.DataFrame(records)[["trade_dt", *NUMERIC_COLS]]
    # 숫자 타입 유지(우측 정렬·정렬 가능): Decimal/None → 숫자형으로 변환
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # 그리드 내부 스크롤이 생기지 않도록 행 수에 맞춰 높이 지정(행 35px + 헤더)
    grid_height = (len(df) + 1) * 35 + 3
    # 천단위 콤마 + 소수 2자리("%,.2f"). NumberColumn은 기본 우측 정렬.
    column_config = {
        "trade_dt": st.column_config.TextColumn("trade_dt"),
        **{
            col: st.column_config.NumberColumn(col, format="%,.2f")
            for col in NUMERIC_COLS
        },
    }
    st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        height=grid_height,
        column_config=column_config,
    )
else:
    st.info("해당 종목의 종가내역이 없습니다.")
