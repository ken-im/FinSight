"""관리자 — 종목마스터 관리 (PRD 7.1)."""

# --- sys.path 부트스트랩 (다른 import보다 먼저) ---
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --------------------------------------------------

import pandas as pd
import streamlit as st

from dashboard.services.auth import require_admin
from dashboard.services.symbol_service import (
    DeleteBlockedError,
    DuplicateSymbolError,
    create_symbol,
    delete_symbol,
    list_symbols,
    update_symbol,
)

st.set_page_config(page_title="종목마스터 관리", page_icon="🗂️", layout="wide")
require_admin()

st.header("🗂️ 종목마스터 관리")

FORM_KEYS = {
    "source": "form_source",
    "symbol": "form_symbol",
    "symbol_nm": "form_nm",
    "remark": "form_remark",
}


def _clear_selection() -> None:
    for key in ("selected_symbol_id", "_bound_id", "price_page", *FORM_KEYS.values()):
        st.session_state.pop(key, None)


# ── 필터 ─────────────────────────────────────────────
with st.expander("필터", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    f_id = c1.text_input("symbol_id")
    f_source = c2.text_input("source")
    f_symbol = c3.text_input("symbol")
    f_nm = c4.text_input("symbol_nm")

rows = list_symbols(
    symbol_id=int(f_id) if f_id.strip().isdigit() else None,
    source=f_source.strip() or None,
    symbol=f_symbol.strip() or None,
    symbol_nm=f_nm.strip() or None,
)

# ── 목록 (행 선택) ───────────────────────────────────
st.subheader("종목 목록")
if rows:
    df = pd.DataFrame(rows)[["symbol_id", "source", "symbol", "symbol_nm", "remark"]]
    event = st.dataframe(
        df,
        hide_index=True,
        use_container_width=True,
        selection_mode="single-row",
        on_select="rerun",
        key="sym_table",
    )
    selected_rows = event.selection.rows
    # 필터 변경/초기화로 행 수가 줄면 위젯에 남은 선택 인덱스가 범위를 벗어날 수 있어 가드
    if selected_rows and selected_rows[0] < len(rows):
        st.session_state["selected_symbol_id"] = rows[selected_rows[0]]["symbol_id"]
else:
    st.info("조건에 해당하는 종목이 없습니다.")

# ── 선택 변경 시 폼 동기화 ───────────────────────────
selected_id = st.session_state.get("selected_symbol_id")
if selected_id != st.session_state.get("_bound_id"):
    st.session_state["_bound_id"] = selected_id
    record = next((r for r in rows if r["symbol_id"] == selected_id), None) or {}
    st.session_state[FORM_KEYS["source"]] = record.get("source", "")
    st.session_state[FORM_KEYS["symbol"]] = record.get("symbol", "")
    st.session_state[FORM_KEYS["symbol_nm"]] = record.get("symbol_nm", "")
    st.session_state[FORM_KEYS["remark"]] = record.get("remark") or ""

# ── 입력 폼 ──────────────────────────────────────────
st.subheader("입력")
st.caption(
    f"선택된 symbol_id: {selected_id}" if selected_id else "선택된 종목 없음 (신규 등록 가능)"
)

c1, c2 = st.columns(2)
c1.text_input("source", key=FORM_KEYS["source"])
c2.text_input("symbol", key=FORM_KEYS["symbol"])
st.text_input("symbol_nm", key=FORM_KEYS["symbol_nm"])
st.text_input("remark", key=FORM_KEYS["remark"])


def _form_values() -> dict:
    return {
        "source": st.session_state.get(FORM_KEYS["source"], "").strip(),
        "symbol": st.session_state.get(FORM_KEYS["symbol"], "").strip(),
        "symbol_nm": st.session_state.get(FORM_KEYS["symbol_nm"], "").strip(),
        "remark": (st.session_state.get(FORM_KEYS["remark"], "") or "").strip() or None,
    }


def _validate(values: dict) -> str | None:
    for field in ("source", "symbol", "symbol_nm"):
        if not values[field]:
            return f"필수 항목 누락: {field}"
    return None


@st.dialog("삭제 확인")
def _confirm_delete(symbol_id: int, label: str) -> None:
    st.write(f"**{label}** (symbol_id={symbol_id}) 을(를) 삭제하시겠습니까?")
    col_ok, col_cancel = st.columns(2)
    if col_ok.button("삭제", type="primary", use_container_width=True):
        try:
            delete_symbol(symbol_id)
        except DeleteBlockedError as exc:
            st.error(str(exc))
            return
        _clear_selection()
        st.session_state["_flash"] = "삭제되었습니다."
        st.rerun()
    if col_cancel.button("취소", use_container_width=True):
        st.rerun()


# ── 버튼 ─────────────────────────────────────────────
b1, b2, b3 = st.columns(3)

if b1.button("신규", use_container_width=True):
    values = _form_values()
    error = _validate(values)
    if error:
        st.warning(error)
    else:
        try:
            new_id = create_symbol(**values)
        except DuplicateSymbolError as exc:
            st.error(str(exc))
        else:
            _clear_selection()
            st.session_state["_flash"] = f"등록되었습니다. (symbol_id={new_id})"
            st.rerun()

if b2.button("수정", use_container_width=True, disabled=selected_id is None):
    values = _form_values()
    error = _validate(values)
    if error:
        st.warning(error)
    else:
        try:
            update_symbol(selected_id, **values)
        except DuplicateSymbolError as exc:
            st.error(str(exc))
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["_flash"] = "수정되었습니다."
            st.rerun()

if b3.button("삭제", use_container_width=True, disabled=selected_id is None):
    values = _form_values()
    _confirm_delete(selected_id, values.get("symbol_nm") or values.get("symbol") or "")

# ── 플래시 메시지 ────────────────────────────────────
if msg := st.session_state.pop("_flash", None):
    st.success(msg)
