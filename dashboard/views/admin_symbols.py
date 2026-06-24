"""\uad00\ub9ac\uc790 \u2014 \uc885\ubaa9\ub9c8\uc2a4\ud130 \uad00\ub9ac (PRD 7.1)."""

import pandas as pd
import streamlit as st

from services.auth import require_admin
from services.symbol_service import (
    DeleteBlockedError,
    DuplicateSymbolError,
    create_symbol,
    delete_symbol,
    list_symbols,
    update_symbol,
)

require_admin()

st.header("\U0001f5c2\ufe0f \uc885\ubaa9\ub9c8\uc2a4\ud130 \uad00\ub9ac")

FORM_KEYS = {
    "source": "form_source",
    "symbol": "form_symbol",
    "symbol_nm": "form_nm",
    "remark": "form_remark",
}


def _clear_selection() -> None:
    for key in ("selected_symbol_id", "_bound_id", "price_page", *FORM_KEYS.values()):
        st.session_state.pop(key, None)


# \u2500\u2500 \ud544\ud130 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
with st.expander("\ud544\ud130", expanded=True):
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

# \u2500\u2500 \ubaa9\ub85d (\ud589 \uc120\ud0dd) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
st.subheader("\uc885\ubaa9 \ubaa9\ub85d")
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
    if selected_rows and selected_rows[0] < len(rows):
        st.session_state["selected_symbol_id"] = rows[selected_rows[0]]["symbol_id"]
else:
    st.info("\uc870\uac74\uc5d0 \ud574\ub2f9\ud558\ub294 \uc885\ubaa9\uc774 \uc5c6\uc2b5\ub2c8\ub2e4.")

# \u2500\u2500 \uc120\ud0dd \ubcc0\uacbd \uc2dc \ud3fc \ub3d9\uae30\ud654 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
selected_id = st.session_state.get("selected_symbol_id")
if selected_id != st.session_state.get("_bound_id"):
    st.session_state["_bound_id"] = selected_id
    record = next((r for r in rows if r["symbol_id"] == selected_id), None) or {}
    st.session_state[FORM_KEYS["source"]] = record.get("source", "")
    st.session_state[FORM_KEYS["symbol"]] = record.get("symbol", "")
    st.session_state[FORM_KEYS["symbol_nm"]] = record.get("symbol_nm", "")
    st.session_state[FORM_KEYS["remark"]] = record.get("remark") or ""

# \u2500\u2500 \uc785\ub825 \ud3fc \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
st.subheader("\uc785\ub825")
st.caption(
    f"\uc120\ud0dd\ub41c symbol_id: {selected_id}" if selected_id else "\uc120\ud0dd\ub41c \uc885\ubaa9 \uc5c6\uc74c (\uc2e0\uaddc \ub4f1\ub85d \uac00\ub2a5)"
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
            return f"\ud544\uc218 \ud56d\ubaa9 \ub204\ub77d: {field}"
    return None


@st.dialog("\uc0ad\uc81c \ud655\uc778")
def _confirm_delete(symbol_id: int, label: str) -> None:
    st.write(f"**{label}** (symbol_id={symbol_id}) \uc744(\ub97c) \uc0ad\uc81c\ud558\uc2dc\uaca0\uc2b5\ub2c8\uae4c?")
    col_ok, col_cancel = st.columns(2)
    if col_ok.button("\uc0ad\uc81c", type="primary", use_container_width=True):
        try:
            delete_symbol(symbol_id)
        except DeleteBlockedError as exc:
            st.error(str(exc))
            return
        _clear_selection()
        st.session_state["_flash"] = "\uc0ad\uc81c\ub418\uc5c8\uc2b5\ub2c8\ub2e4."
        st.rerun()
    if col_cancel.button("\ucde8\uc18c", use_container_width=True):
        st.rerun()


# \u2500\u2500 \ubc84\ud2bc \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
b1, b2, b3 = st.columns(3)

if b1.button("\uc2e0\uaddc", use_container_width=True):
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
            st.session_state["_flash"] = f"\ub4f1\ub85d\ub418\uc5c8\uc2b5\ub2c8\ub2e4. (symbol_id={new_id})"
            st.rerun()

if b2.button("\uc218\uc815", use_container_width=True, disabled=selected_id is None):
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
            st.session_state["_flash"] = "\uc218\uc815\ub418\uc5c8\uc2b5\ub2c8\ub2e4."
            st.rerun()

if b3.button("\uc0ad\uc81c", use_container_width=True, disabled=selected_id is None):
    values = _form_values()
    _confirm_delete(selected_id, values.get("symbol_nm") or values.get("symbol") or "")

# \u2500\u2500 \ud50c\ub798\uc2dc \uba54\uc2dc\uc9c0 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
if msg := st.session_state.pop("_flash", None):
    st.success(msg)
