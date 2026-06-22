"""FinSight Dashboard - main entry point.

Run: uv run streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# sys.path bootstrap: ROOT (for src.*) and DASH (for finsight_lib.*, services.*)
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
DASH = ROOT / "dashboard"
for _p in (str(ROOT), str(DASH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.connection import get_engine          # noqa: F401 - triggers secrets bridge
from services.price_service import get_series, list_symbol_coverage
from services.symbol_service import list_symbols
from finsight_lib.palette import CHART_THEMES, COLOR_EMOJI, COLOR_MAP, RAINBOW, RAINBOW_NAMES
from finsight_lib.periods import DEFAULT_PRESET, DIRECT_LABEL, PRESETS, from_date_by_preset
from finsight_lib.transform import normalize_100, to_wide

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSight",
    page_icon="\U0001f3e0",   # home emoji
    layout="wide",
)

_MAX_SELECT = 10
_EDITOR_VER = "editor_ver"
_DEFAULT_CODES = ["KS11", "KQ11", "US500", "VIX"]


# ── Cached symbol loader ──────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def _load_symbols() -> list[dict]:
    return list_symbols()


# ── Symbol data ───────────────────────────────────────────────────────────────
all_syms = _load_symbols()
if not all_syms:
    st.error("\uc885\ubaa9 \uc815\ubcf4\ub97c \ubd88\ub7ec\uc62c \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. DB \uc5f0\uacb0 \ubc0f \uc2dc\ub4dc \ub4f1\ub85d\uc744 \ud655\uc778\ud558\uc138\uc694.")
    st.stop()

all_ids:    list[int]       = [s["symbol_id"]  for s in all_syms]
id_to_nm:   dict[int, str]  = {s["symbol_id"]: s["symbol_nm"] for s in all_syms}
id_to_sym:  dict[int, str]  = {s["symbol_id"]: s["symbol"]    for s in all_syms}
code_to_id: dict[str, int]  = {s["symbol"]: s["symbol_id"]    for s in all_syms}
default_ids: list[int]      = [code_to_id[c] for c in _DEFAULT_CODES if c in code_to_id]


# ── session_state init ────────────────────────────────────────────────────────
if "selected_order" not in st.session_state:
    st.session_state["selected_order"] = list(default_ids)
if _EDITOR_VER not in st.session_state:
    st.session_state[_EDITOR_VER] = 0
if "chart_theme" not in st.session_state:
    st.session_state["chart_theme"] = "Dark"
if "color_map" not in st.session_state:
    st.session_state["color_map"] = {}          # {symbol_id: hex_color}


def _ensure_colors(sel_order: list[int], color_map: dict) -> None:
    """Auto-assign RAINBOW colors to newly selected symbols (no duplicates)."""
    used = {color_map[s] for s in sel_order if s in color_map}
    for sid in sel_order:
        if sid not in color_map:
            for c in RAINBOW_NAMES:
                if c not in used:
                    color_map[sid] = c
                    used.add(c)
                    break
            else:
                color_map[sid] = RAINBOW_NAMES[0]


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # Header + counter
    sel_order: list[int] = st.session_state["selected_order"]
    n_sel = len(sel_order)
    st.markdown(
        f"#### \uc2dc\uc7a5\uc9c0\ud45c \uc120\ud0dd &nbsp; `{n_sel} / {_MAX_SELECT}`",
        unsafe_allow_html=True,
    )

    # Action buttons: [전체] [해제] [기본값]
    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("\uc804\uccb4", use_container_width=True):        # 전체
        st.session_state["selected_order"] = list(all_ids[:_MAX_SELECT])
        st.session_state[_EDITOR_VER] += 1
    if bc2.button("\ud574\uc81c", use_container_width=True):        # 해제
        st.session_state["selected_order"] = []
        st.session_state[_EDITOR_VER] += 1
    if bc3.button("\uae30\ubcf8\uac12", use_container_width=True): # 기본값
        st.session_state["selected_order"] = list(default_ids)
        st.session_state[_EDITOR_VER] += 1

    # Ensure colors for current selection
    sel_order  = st.session_state["selected_order"]
    color_map: dict = st.session_state["color_map"]
    _ensure_colors(sel_order, color_map)
    sel_set = set(sel_order)

    # Load coverage
    try:
        cov_list = list_symbol_coverage()
        cov_map  = {c["symbol_id"]: c for c in cov_list}
    except Exception:
        cov_map = {}

    # Build data_editor DataFrame
    rows = []
    for s in all_syms:
        sid    = s["symbol_id"]
        is_sel = sid in sel_set
        cov    = cov_map.get(sid, {})
        rows.append({
            "\uc120\ud0dd": is_sel,                              # 선택
            "\uc0c9\uc0c1": color_map.get(sid, RAINBOW_NAMES[0]), # 색상 (English name)
            "\u25cf": COLOR_EMOJI.get(color_map.get(sid, RAINBOW_NAMES[0]), "\u26aa") if is_sel else "\u26aa",
            "SYMBOL":        s["symbol"],
            "\uc790\uc0b0\uba85": s["symbol_nm"],               # 자산명
            "FROM":          cov.get("from_dt", "-"),
            "TO":            cov.get("to_dt",   "-"),
            "\uac74\uc218": cov.get("cnt", 0),                   # 건수
            "_id":           sid,
        })

    df_sym = pd.DataFrame(rows)

    edited = st.data_editor(
        df_sym,
        key=f"sym_ed_{st.session_state[_EDITOR_VER]}",
        column_config={
            "\uc120\ud0dd": st.column_config.CheckboxColumn(
                "\u2713", width="small"),
            "\uc0c9\uc0c1": st.column_config.SelectboxColumn(
                "\uc0c9\uc0c1",  # 색상
                options=RAINBOW_NAMES,
                width="small",
            ),
            "SYMBOL":           st.column_config.TextColumn(
                "SYMBOL", width="small", disabled=True),
            "\uc790\uc0b0\uba85": st.column_config.TextColumn(
                "\uc790\uc0b0\uba85", disabled=True),           # 자산명
            "FROM":             st.column_config.TextColumn(
                "FROM", width="small", disabled=True),
            "TO":               st.column_config.TextColumn(
                "TO",   width="small", disabled=True),
            "\uac74\uc218":   st.column_config.NumberColumn(
                "\uac74\uc218", width="small", format="%d", disabled=True),
            "_id":              None,
        },
        hide_index=True,
        width="stretch",
        height=490,
    )

    # Process edits: preserve selection order, append new items at end
    new_sel_set = set(edited.loc[edited["\uc120\ud0dd"], "_id"].tolist())
    prev_order  = st.session_state["selected_order"]
    kept  = [sid for sid in prev_order if sid in new_sel_set]
    added = [sid for sid in new_sel_set if sid not in set(prev_order)]
    new_order = kept + added

    if len(new_order) > _MAX_SELECT:
        new_order = new_order[:_MAX_SELECT]
        st.toast(
            f"\ucd5c\ub300 {_MAX_SELECT}\uac1c\uae4c\uc9c0 "
            "\uc120\ud0dd \uac00\ub2a5\ud569\ub2c8\ub2e4.",
            icon="\u26a0\ufe0f",
        )

    st.session_state["selected_order"] = new_order
    selected_ids: list[int] = new_order

    # Update color_map from user changes
    for _, row in edited.loc[edited["\uc120\ud0dd"]].iterrows():
        sid = int(row["_id"])
        if row["\uc0c9\uc0c1"] in RAINBOW_NAMES:
            color_map[sid] = row["\uc0c9\uc0c1"]

    st.divider()

    # Period settings
    st.markdown("#### \uae30\uac04 \uc124\uc815")  # 기간 설정
    to_date: date = st.date_input("\uc885\ub8cc\uc77c", value=date.today())  # 종료일
    preset: str = st.selectbox(
        "\uae30\uac04 \ud504\ub9ac\uc14b",  # 기간 프리셋
        options=PRESETS,
        index=PRESETS.index(DEFAULT_PRESET),
        key="period_preset",
    )
    if preset == DIRECT_LABEL:
        try:
            default_from = to_date.replace(year=to_date.year - 1)
        except ValueError:
            default_from = to_date.replace(year=to_date.year - 1, day=28)
        from_date: date = st.date_input("\uc2dc\uc791\uc77c", value=default_from)  # 시작일
    else:
        from_date = from_date_by_preset(to_date, preset)
        st.caption(f"\uc2dc\uc791\uc77c: {from_date.strftime('%Y-%m-%d')}")  # 시작일

    if from_date > to_date:
        st.error("\uc2dc\uc791\uc77c\uc774 \uc885\ub8cc\uc77c\ubcf4\ub2e4 \ud074 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
        from_date = to_date

    st.divider()

    # Display mode
    st.markdown("#### \ud45c\uc2dc \ubc29\uc2dd")  # 표시 방식
    normalize: bool = st.toggle(
        "\uc815\uaddc\ud654 (\uae30\uc900 100)",  # 정규화 (기준 100)
        value=True,
        key="normalize_toggle",
    )
    if not normalize:
        st.warning(
            "\uc6d0\ubcf8 \uc885\uac00\ub294 \ub2e8\uc704 \ucc28\uc774\ub85c "
            "\ube44\uad50\uac00 \uc5b4\ub835\uc2b5\ub2c8\ub2e4. "
            "\uc815\uaddc\ud654\ub97c \uad8c\uc7a5\ud569\ub2c8\ub2e4."
        )

    st.divider()

    # Admin links (bottom of sidebar)
    st.page_link(
        "pages/1_admin_symbols.py",
        label="\U0001f5c2\ufe0f \uc885\ubaa9\ub9c8\uc2a4\ud130 \uad00\ub9ac",  # 🗂️ 종목마스터 관리
    )
    st.page_link(
        "pages/2_admin_prices.py",
        label="\U0001f4ca \uc885\uac00\ub0b4\uc5ed \uc870\ud68c",  # 📊 종가내역 조회
    )


# ── Main area ─────────────────────────────────────────────────────────────────
title_col, theme_col = st.columns([6, 2])
with title_col:
    st.markdown("### \U0001f4c8 FinSight \ub300\uc2dc\ubcf4\ub4dc")  # 📈 FinSight 대시보드
with theme_col:
    theme_choice: str = st.radio(
        "\ucc28\ud2b8 \ubc30\uacbd",  # 차트 배경
        options=["Dark", "Light"],
        index=0 if st.session_state["chart_theme"] == "Dark" else 1,
        horizontal=True,
        key="chart_theme_radio",
    )
    st.session_state["chart_theme"] = theme_choice

# No symbols selected
if not selected_ids:
    st.info(
        "\uc88c\uce21 \uc0ac\uc774\ub4dc\ubc14\uc5d0\uc11c "
        "\uc885\ubaa9\uc744 \uc120\ud0dd\ud558\uba74 "
        "\ucc28\ud2b8\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4."
    )
    st.stop()

# Fetch data
from_str = from_date.strftime("%Y%m%d")
to_str   = to_date.strftime("%Y%m%d")

try:
    rows_data = get_series(tuple(sorted(selected_ids)), from_str, to_str)
except Exception as exc:
    st.error(f"\ub370\uc774\ud130 \uc870\ud68c \uc624\ub958: {exc}")
    st.stop()

if not rows_data:
    st.warning(
        f"\uc120\ud0dd\ud55c \uae30\uac04({from_date} ~ {to_date})\uc5d0 "
        "\ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4."
    )
    st.stop()

# Transform
id_nm_map  = {sid: id_to_nm[sid] for sid in selected_ids}
wide_df    = to_wide(rows_data, id_nm_map)
display_df = normalize_100(wide_df) if normalize else wide_df

# Build Plotly chart
t   = CHART_THEMES[st.session_state["chart_theme"]]
fig = go.Figure()

for sid in selected_ids:
    nm = id_to_nm[sid]
    if nm not in display_df.columns:
        continue
    fig.add_trace(
        go.Scatter(
            x=display_df.index,
            y=display_df[nm],
            mode="lines",
            name=nm,
            line=dict(color=COLOR_MAP.get(color_map.get(sid, RAINBOW_NAMES[0]), RAINBOW[0]), width=1.8),
            connectgaps=False,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "\ub0a0\uc9dc: %{x|%Y-%m-%d}<br>"
                "%{y:.2f}<extra></extra>"
            ),
        )
    )

y_title = (
    "\uc815\uaddc\ud654 \uc9c0\uc218 (\uae30\uc900 100)"
    if normalize else
    "\uc885\uac00/\uc9c0\ud45c"
)
fig.update_layout(
    paper_bgcolor=t["paper_bgcolor"],
    plot_bgcolor =t["plot_bgcolor"],
    font=dict(
        color=t["font_color"],
        family="-apple-system, 'Segoe UI', Roboto, 'Noto Sans KR', sans-serif",
        size=12,
    ),
    xaxis=dict(
        showgrid=True,
        gridcolor=t["grid_color"],
        linecolor=t["line_color"],
        tickfont=dict(color=t["font_color"]),
        title=dict(
            text="\ub0a0\uc9dc",  # 날짜
            standoff=12,
            font=dict(color=t["font_color"]),
        ),
        rangeslider=dict(
            visible=True,
            bgcolor=t["slider_bg"],
            bordercolor=t["line_color"],
            thickness=0.06,
        ),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor=t["grid_color"],
        linecolor=t["line_color"],
        tickfont=dict(color=t["font_color"]),
        title=dict(text=y_title, standoff=10, font=dict(color=t["font_color"])),
        hoverformat=".2f",
    ),
    legend=dict(
        bgcolor=t["legend_bg"],
        bordercolor=t["line_color"],
        borderwidth=1,
        x=0.01, y=0.99,
        xanchor="left", yanchor="top",
        font=dict(color=t["font_color"]),
    ),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor=t["hover_bg"],
        bordercolor=t["line_color"],
        font=dict(color=t["hover_font"]),
    ),
    margin=dict(l=65, r=20, t=16, b=60),
    height=580,
    autosize=True,
)

st.plotly_chart(
    fig,
    width="stretch",
    config=dict(
        responsive=True,
        displayModeBar=True,
        modeBarButtonsToRemove=["select2d", "lasso2d"],
        displaylogo=False,
        toImageButtonOptions=dict(
            format="png", filename="finsight_chart", scale=2,
        ),
    ),
)

# CSV download
csv_df = display_df.copy()
csv_df.index = csv_df.index.strftime("%Y-%m-%d")
csv_df.index.name = "\ub0a0\uc9dc"  # 날짜
csv_df = csv_df.reset_index()

st.download_button(
    label="\U0001f4e5 CSV \ub2e4\uc6b4\ub85c\ub4dc",  # 📥 CSV 다운로드
    data=csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="finsight_chart.csv",
    mime="text/csv",
)
