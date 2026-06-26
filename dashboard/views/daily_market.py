"""\uc2dc\uc7a5\uc9c0\ud45c\uc77c\ubcc4\uc2dc\uc138 \u2014 \ub2e8\uc77c \uc9c0\ud45c \uae30\uac04 \ubc94\uc704 \uc77c\ubcc4 \uc2dc\uc138 \uc870\ud68c."""

import math
from datetime import date

import pandas as pd
import streamlit as st

from dashboard.services.price_service import PAGE_SIZE, list_daily_prices
from dashboard.services.symbol_service import list_symbols
from dashboard.finsight_lib.periods import DEFAULT_PRESET, DIRECT_LABEL, PRESETS, from_date_by_preset


@st.cache_data(ttl=86400, show_spinner=False)
def _load_symbols() -> list[dict]:
    return list_symbols()


symbols = _load_symbols()
if not symbols:
    st.info("\ub4f1\ub85d\ub41c \uc885\ubaa9\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. \uba3c\uc800 \uc885\ubaa9\ub9c8\uc2a4\ud130\uc5d0\uc11c \uc885\ubaa9\uc744 \ub4f1\ub85d\ud558\uc138\uc694.")
    st.stop()

st.header("\U0001f4cb \uc2dc\uc7a5\uc9c0\ud45c\uc77c\ubcc4\uc2dc\uc138")

# \u2500\u2500 \uc870\ud68c \uc870\uac74 (sidebar) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
with st.sidebar:
    st.markdown("#### \uc2dc\uc7a5\uc9c0\ud45c \uc120\ud0dd")
    options = {
        f'{s["symbol"]} \u2014 {s["symbol_nm"]}': s["symbol_id"]
        for s in symbols
    }
    labels = list(options.keys())
    chosen_label = st.selectbox(
        "\uc9c0\ud45c \uc120\ud0dd",
        labels,
        key="dm_symbol",
        label_visibility="collapsed",
    )
    chosen_id = options[chosen_label]

    st.divider()

    st.markdown("#### \uae30\uac04 \uc124\uc815")
    to_date: date = st.date_input("\uc885\ub8cc\uc77c", value=date.today(), key="dm_to")
    preset: str = st.selectbox(
        "\uae30\uac04 \ud504\ub9ac\uc14b",
        options=PRESETS,
        index=PRESETS.index(DEFAULT_PRESET),
        key="dm_preset",
    )
    if preset == DIRECT_LABEL:
        try:
            default_from = to_date.replace(year=to_date.year - 1)
        except ValueError:
            default_from = to_date.replace(year=to_date.year - 1, day=28)
        from_date: date = st.date_input("\uc2dc\uc791\uc77c", value=default_from, min_value=date(1990, 1, 2), key="dm_from")
    else:
        from_date = from_date_by_preset(to_date, preset)
        st.caption(f"\uc2dc\uc791\uc77c: {from_date.strftime('%Y-%m-%d')}")

    if from_date > to_date:
        st.error("\uc2dc\uc791\uc77c\uc774 \uc885\ub8cc\uc77c\ubcf4\ub2e4 \ud074 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
        from_date = to_date

from_str = from_date.strftime("%Y%m%d")
to_str   = to_date.strftime("%Y%m%d")

# \u2500\u2500 \ud398\uc774\uc9d5 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
if "dm_page" not in st.session_state:
    st.session_state["dm_page"] = 1

records, total = list_daily_prices(chosen_id, from_str, to_str, page=st.session_state["dm_page"])
total_pages = max(1, math.ceil(total / PAGE_SIZE))
page = min(max(1, st.session_state["dm_page"]), total_pages)
st.session_state["dm_page"] = page

c_first, c_prev, c_info, c_next, c_last = st.columns([1, 1, 3, 1, 1])
if c_first.button("<<", use_container_width=True, disabled=page <= 1, help="\uccab \ud398\uc774\uc9c0"):
    st.session_state["dm_page"] = 1
    st.rerun()
if c_prev.button("\u25c0", use_container_width=True, disabled=page <= 1, help="\uc774\uc804 \ud398\uc774\uc9c0"):
    st.session_state["dm_page"] = page - 1
    st.rerun()
c_info.markdown(
    f"<div style='text-align:center'>\ud398\uc774\uc9c0 <b>{page}</b> / {total_pages} \u00b7 \ucd1d <b>{total:,}</b>\uac74</div>",
    unsafe_allow_html=True,
)
if c_next.button("\u25b6", use_container_width=True, disabled=page >= total_pages, help="\ub2e4\uc74c \ud398\uc774\uc9c0"):
    st.session_state["dm_page"] = page + 1
    st.rerun()
if c_last.button(">>", use_container_width=True, disabled=page >= total_pages, help="\ub9c8\uc9c0\ub9c9 \ud398\uc774\uc9c0"):
    st.session_state["dm_page"] = total_pages
    st.rerun()

# \u2500\u2500 \ub370\uc774\ud130 \ud14c\uc774\ube14 \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
NUMERIC_COLS = [
    "close_price",
    "open_price",
    "high_price",
    "low_price",
    "volume",
    "trade_amount",
    "change_rate",
]

if records:
    df = pd.DataFrame(records)[["trade_dt", *NUMERIC_COLS]]
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    grid_height = (len(df) + 1) * 35 + 3
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
    st.info("\ud574\ub2f9 \uae30\uac04\uc5d0 \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.")
