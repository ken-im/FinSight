"""FinSight Dashboard — st.navigation() entry point.

Run: uv run streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="FinSight", page_icon="\U0001f3e0", layout="wide")

# sys.path bootstrap: ROOT (for src.*) and DASH (for finsight_lib.*, services.*)
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
DASH = ROOT / "dashboard"
for _p in (str(ROOT), str(DASH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

page_trend = st.Page("views/market_trend.py", title="\uc2dc\uc7a5\uc9c0\ud45c\ud2b8\ub80c\ub4dc", icon="\U0001f3e0", default=True)
page_ma    = st.Page("views/ma_analysis.py",  title="\uc774\ub3d9\ud3c9\uade0\ubd84\uc11d",       icon="\U0001f4c8")
page_daily = st.Page("views/daily_market.py", title="\uc2dc\uc7a5\uc9c0\ud45c\uc77c\ubcc4\uc2dc\uc138",   icon="\U0001f4cb")
page_admin = st.Page("views/admin_symbols.py", title="Admin Symbols", icon="\U0001f5c2\ufe0f")

pg = st.navigation(
    [page_trend, page_ma, page_daily, page_admin],
    position="hidden",
)

with st.sidebar:
    st.page_link(page_trend, label="\uc2dc\uc7a5\uc9c0\ud45c\ud2b8\ub80c\ub4dc")
    st.page_link(page_ma,    label="\uc774\ub3d9\ud3c9\uade0\ubd84\uc11d")
    st.page_link(page_daily, label="\uc2dc\uc7a5\uc9c0\ud45c\uc77c\ubcc4\uc2dc\uc138")
    st.divider()

pg.run()

with st.sidebar:
    st.divider()
    st.page_link(page_admin, label="Admin Symbols")
