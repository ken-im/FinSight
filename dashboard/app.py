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

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinSight",
    page_icon="🏠",
    layout="wide",
)

_MAX_SELECT   = 10
_DEFAULT_CODES = ["KS11", "KQ11", "US500", "VIX"]
_MS_KEY       = "ms_symbols"   # multiselect widget key


# ─── Cached loaders ───────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def _load_symbols() -> list[dict]:
    return list_symbols()


# ─── Symbol master data ───────────────────────────────────────────────────────
all_syms = _load_symbols()
if not all_syms:
    st.error(
        "종목 정보를 불러올 수 없습니다. "
        "DB 연결 및 시드 등록을 확인하세요."
    )
    st.stop()

all_ids:    list[int]       = [s["symbol_id"]  for s in all_syms]
id_to_nm:   dict[int, str]  = {s["symbol_id"]: s["symbol_nm"] for s in all_syms}
id_to_sym:  dict[int, str]  = {s["symbol_id"]: s["symbol"]    for s in all_syms}
code_to_id: dict[str, int]  = {s["symbol"]: s["symbol_id"]    for s in all_syms}
default_ids: list[int]      = [code_to_id[c] for c in _DEFAULT_CODES if c in code_to_id]


# ─── session_state init ───────────────────────────────────────────────────────
if _MS_KEY not in st.session_state:
    st.session_state[_MS_KEY] = list(default_ids)
if "chart_theme" not in st.session_state:
    st.session_state["chart_theme"] = "Dark"


def _init_colors(sel_ids: list[int]) -> None:
    """Assign RAINBOW colors to newly selected symbols (no duplicates)."""
    used = {st.session_state.get(f"cs_{s}") for s in sel_ids if f"cs_{s}" in st.session_state}
    for sid in sel_ids:
        key = f"cs_{sid}"
        if key not in st.session_state:
            for c in RAINBOW_NAMES:
                if c not in used:
                    st.session_state[key] = c
                    used.add(c)
                    break
            else:
                st.session_state[key] = RAINBOW_NAMES[0]


# ─── Reference table HTML builder ────────────────────────────────────────────
def _coverage_table_html(all_syms: list[dict], cov_map: dict) -> str:
    css = (
        "<style>"
        ".fst{width:100%;border-collapse:collapse;font-size:0.71rem;}"
        ".fst th{padding:3px 5px;border-bottom:2px solid #444;color:#888;"
        "font-weight:500;text-align:left;white-space:nowrap;}"
        ".fst td{padding:2px 5px;border-bottom:1px solid #2a2a2a;white-space:nowrap;}"
        ".fst .nm{font-weight:700;}"
        ".fst .num{text-align:right;font-variant-numeric:tabular-nums;}"
        ".fst .dt{color:#aaa;}"
        "</style>"
    )
    rows = []
    for s in all_syms:
        sid = s["symbol_id"]
        cov = cov_map.get(sid, {})
        fd = cov.get("from_dt", "-")
        td = cov.get("to_dt",   "-")
        if fd and len(fd) == 8:
            fd = f"{fd[:4]}-{fd[4:6]}-{fd[6:]}"
        if td and len(td) == 8:
            td = f"{td[:4]}-{td[4:6]}-{td[6:]}"
        cnt = cov.get("cnt", 0)
        cnt_str = f"{cnt:,}" if cnt else "-"
        rows.append(
            f"<tr>"
            f"<td>{s['symbol']}</td>"
            f"<td class='nm'>{s['symbol_nm']}</td>"
            f"<td class='dt'>{fd}</td>"
            f"<td class='dt'>{td}</td>"
            f"<td class='num'>{cnt_str}</td>"
            f"</tr>"
        )
    body = "".join(rows)
    return (
        css
        + "<table class='fst'>"
        + "<thead><tr>"
        + "<th>Symbol</th><th>지표명</th>"
        + "<th>From</th><th>To</th><th class='num'>건수</th>"
        + "</tr></thead>"
        + f"<tbody>{body}</tbody>"
        + "</table>"
    )


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── 1. Symbol multiselect ──────────────────────────────────────────────────
    n_sel = len(st.session_state[_MS_KEY])
    st.markdown(
        f"#### 시장지표 선택 &nbsp; `{n_sel} / {_MAX_SELECT}`",
        unsafe_allow_html=True,
    )

    # Action buttons
    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("전체", use_container_width=True):
        st.session_state[_MS_KEY] = list(all_ids[:_MAX_SELECT])
    if bc2.button("해제", use_container_width=True):
        st.session_state[_MS_KEY] = []
    if bc3.button("기본값", use_container_width=True):
        st.session_state[_MS_KEY] = list(default_ids)

    # Multiselect (Google Trends style)
    selected_ids: list[int] = st.multiselect(
        "지표 선택",
        options=all_ids,
        key=_MS_KEY,
        format_func=lambda sid: f"{id_to_sym[sid]} — {id_to_nm[sid]}",
        max_selections=_MAX_SELECT,
        label_visibility="collapsed",
        placeholder="지표를 선택하세요 (최대 10개)",
    )

    # ── 2. Color assignment ────────────────────────────────────────────────────
    if selected_ids:
        _init_colors(selected_ids)
        st.markdown(
            "<div style='font-size:0.78rem;font-weight:600;margin:6px 0 2px'>"
            "지표별 색상 지정</div>",
            unsafe_allow_html=True,
        )
        for sid in selected_ids:
            color_name = st.session_state.get(f"cs_{sid}", RAINBOW_NAMES[0])
            emoji      = COLOR_EMOJI.get(color_name, "⚪")
            lc, rc = st.columns([4, 5])
            lc.markdown(
                f"<div style='font-size:0.78rem;padding-top:6px'>"
                f"{emoji}&nbsp;<b>{id_to_sym[sid]}</b>&nbsp;"
                f"<span style='color:#888'>{id_to_nm[sid]}</span></div>",
                unsafe_allow_html=True,
            )
            rc.selectbox(
                f"color_{sid}",
                options=RAINBOW_NAMES,
                key=f"cs_{sid}",
                label_visibility="collapsed",
            )

    st.divider()

    # ── 3. Period settings ────────────────────────────────────────────────────
    st.markdown("#### 기간 설정")
    to_date: date = st.date_input("종료일", value=date.today())
    preset: str = st.selectbox(
        "기간 프리셋",
        options=PRESETS,
        index=PRESETS.index(DEFAULT_PRESET),
        key="period_preset",
    )
    if preset == DIRECT_LABEL:
        try:
            default_from = to_date.replace(year=to_date.year - 1)
        except ValueError:
            default_from = to_date.replace(year=to_date.year - 1, day=28)
        from_date: date = st.date_input("시작일", value=default_from)
    else:
        from_date = from_date_by_preset(to_date, preset)
        st.caption(f"시작일: {from_date.strftime('%Y-%m-%d')}")

    if from_date > to_date:
        st.error("시작일이 종료일보다 클 수 없습니다.")
        from_date = to_date

    st.divider()

    # ── 4. Display mode ────────────────────────────────────────────────────────
    st.markdown("#### 표시 방식")
    normalize: bool = st.toggle(
        "정규화 (기준 100)",
        value=True,
        key="normalize_toggle",
    )
    if not normalize:
        st.warning(
            "원본 종가는 단위 차이로 "
            "비교가 어렵습니다. "
            "정규화를 권장합니다."
        )

    st.divider()

    # ── 5. Reference coverage table ───────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:600;margin-bottom:4px'>"
        "지표 데이터 보유현황</div>",
        unsafe_allow_html=True,
    )
    try:
        cov_list = list_symbol_coverage()
        cov_map  = {c["symbol_id"]: c for c in cov_list}
    except Exception:
        cov_map  = {}

    st.markdown(_coverage_table_html(all_syms, cov_map), unsafe_allow_html=True)

    st.divider()

    # ── 6. Admin links ────────────────────────────────────────────────────────
    st.page_link(
        "pages/1_admin_symbols.py",
        label="🗂️ 종목마스터 관리",
    )
    st.page_link(
        "pages/2_admin_prices.py",
        label="📊 종가내역 조회",
    )


# ─── Main area ────────────────────────────────────────────────────────────────
title_col, theme_col = st.columns([6, 2])
with title_col:
    st.markdown("### 📈 FinSight 대시보드")
with theme_col:
    theme_choice: str = st.radio(
        "차트 배경",
        options=["Dark", "Light"],
        index=0 if st.session_state["chart_theme"] == "Dark" else 1,
        horizontal=True,
        key="chart_theme_radio",
    )
    st.session_state["chart_theme"] = theme_choice

# No symbols selected
if not selected_ids:
    st.info(
        "좌측 사이드바에서 "
        "지표를 선택하면 차트가 표시됩니다."
    )
    st.stop()

# ─── Fetch data ───────────────────────────────────────────────────────────────
from_str = from_date.strftime("%Y%m%d")
to_str   = to_date.strftime("%Y%m%d")

try:
    rows_data = get_series(tuple(sorted(selected_ids)), from_str, to_str)
except Exception as exc:
    st.error(f"데이터 조회 오류: {exc}")
    st.stop()

if not rows_data:
    st.warning(
        f"선택한 기간({from_date} ~ {to_date})에 "
        "데이터가 없습니다."
    )
    st.stop()

# ─── Transform ────────────────────────────────────────────────────────────────
id_nm_map  = {sid: id_to_nm[sid] for sid in selected_ids}
wide_df    = to_wide(rows_data, id_nm_map)
display_df = normalize_100(wide_df) if normalize else wide_df

# ─── Plotly chart ─────────────────────────────────────────────────────────────
t   = CHART_THEMES[st.session_state["chart_theme"]]
fig = go.Figure()

for sid in selected_ids:
    nm = id_to_nm[sid]
    if nm not in display_df.columns:
        continue
    color_name = st.session_state.get(f"cs_{sid}", RAINBOW_NAMES[0])
    color_hex  = COLOR_MAP.get(color_name, RAINBOW[0])
    fig.add_trace(
        go.Scatter(
            x=display_df.index,
            y=display_df[nm],
            mode="lines",
            name=nm,
            line=dict(color=color_hex, width=1.8),
            connectgaps=False,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "날짜: %{x|%Y-%m-%d}<br>"
                "%{y:.2f}<extra></extra>"
            ),
        )
    )

y_title = (
    "정규화 지수 (기준 100)"
    if normalize else
    "종가/지표"
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
            text="날짜",
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
        toImageButtonOptions=dict(format="png", filename="finsight_chart", scale=2),
    ),
)

# ─── CSV download ─────────────────────────────────────────────────────────────
csv_df = display_df.copy()
csv_df.index = csv_df.index.strftime("%Y-%m-%d")
csv_df.index.name = "날짜"
csv_df = csv_df.reset_index()

st.download_button(
    label="📥 CSV 다운로드",
    data=csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="finsight_chart.csv",
    mime="text/csv",
)
