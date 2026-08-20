"""이동평균분석 — 단일 지표 SMA 차트."""

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.services.price_service import get_series
from dashboard.services.symbol_service import list_symbols
from dashboard.finsight_lib.palette import CHART_THEMES
from dashboard.finsight_lib.periods import DEFAULT_PRESET, DIRECT_LABEL, PRESETS, from_date_by_preset
from dashboard.finsight_lib.transform import calc_sma
from dashboard.finsight_lib.ma_config import (
    MA_DEFAULTS,
    MA_LINE_STYLES,
    MA_OPTION_NAMES,
    MA_OPTIONS,
    PRICE_LINE_STYLE,
)
from dashboard.finsight_lib.market_summary import (
    OUTLOOK_ICONS,
    compute_long_term_outlook,
    compute_short_term_summary,
)


@st.cache_data(ttl=86400, show_spinner=False)
def _load_symbols() -> list[dict]:
    return list_symbols()


symbols = _load_symbols()
if not symbols:
    st.info(
        "등록된 종목이 없습니다. "
        "먼저 종목마스터에서 종목을 등록하세요."
    )
    st.stop()

id_to_nm:  dict[int, str] = {s["symbol_id"]: s["symbol_nm"] for s in symbols}
id_to_sym: dict[int, str] = {s["symbol_id"]: s["symbol"]    for s in symbols}

if "chart_theme" not in st.session_state:
    st.session_state["chart_theme"] = "Dark"

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    # 1. Symbol select (single)
    st.markdown("#### 시장지표 선택")
    sym_options = {
        f'{s["symbol"]} — {s["symbol_nm"]}': s["symbol_id"]
        for s in symbols
    }
    sym_labels = list(sym_options.keys())
    chosen_label = st.selectbox(
        "지표 선택",
        sym_labels,
        key="ma_symbol",
        label_visibility="collapsed",
    )
    chosen_id = sym_options[chosen_label]

    st.divider()

    # 2. Period settings (reuse periods.py)
    st.markdown("#### 기간 설정")
    to_date: date = st.date_input("종료일", value=date.today(), key="ma_to")
    preset: str = st.selectbox(
        "기간 프리셋",
        options=PRESETS,
        index=PRESETS.index(DEFAULT_PRESET),
        key="ma_preset",
    )
    if preset == DIRECT_LABEL:
        try:
            default_from = to_date.replace(year=to_date.year - 1)
        except ValueError:
            default_from = to_date.replace(year=to_date.year - 1, day=28)
        from_date: date = st.date_input("시작일", value=default_from, min_value=date(1990, 1, 2), key="ma_from")
    else:
        from_date = from_date_by_preset(to_date, preset)
        st.caption(f"시작일: {from_date.strftime('%Y-%m-%d')}")

    if from_date > to_date:
        st.error("시작일이 종료일보다 클 수 없습니다.")
        from_date = to_date

    st.divider()

    # 3. MA line settings
    st.markdown("#### 이동평균선 설정")
    ma_selections: list[str] = []
    for i in range(3):
        default_idx = MA_OPTION_NAMES.index(MA_DEFAULTS[i]) if MA_DEFAULTS[i] in MA_OPTION_NAMES else 0
        sel = st.selectbox(
            f"이동평균 {i + 1}",
            options=MA_OPTION_NAMES,
            index=default_idx,
            key=f"ma_sel_{i}",
        )
        opt = MA_OPTIONS[sel]
        st.caption(f"  {opt['label']}, {opt['window']}일")
        ma_selections.append(sel)

# ── Data fetch with buffer ──────────────────────────────────────────────────
ma_windows: dict[str, int] = {}
for sel in ma_selections:
    opt = MA_OPTIONS[sel]
    ma_windows[opt["label"]] = opt["window"]

max_window = max(ma_windows.values())
buffer_days = int(max_window * 1.5)
extended_from = from_date - timedelta(days=buffer_days)

ext_from_str = extended_from.strftime("%Y%m%d")
to_str       = to_date.strftime("%Y%m%d")
from_str     = from_date.strftime("%Y%m%d")

try:
    rows_data = get_series((chosen_id,), ext_from_str, to_str)
except Exception as exc:
    st.error(f"데이터 조회 오류: {exc}")
    st.stop()

if not rows_data:
    st.warning(
        f"선택한 기간에 데이터가 없습니다."
    )
    st.stop()

# ── Build DataFrame + SMA ───────────────────────────────────────────────────
df = pd.DataFrame(rows_data)
df["trade_dt"]    = pd.to_datetime(df["trade_dt"], format="%Y%m%d")
df["close_price"] = df["close_price"].astype(float)
df = df.sort_values("trade_dt").set_index("trade_dt")

df = calc_sma(df, "close_price", ma_windows)

# Trim to display range
display_from = pd.Timestamp(from_date)
display_to   = pd.Timestamp(to_date)
chart_df = df.loc[display_from:display_to].copy()

if chart_df.empty:
    st.warning("표시 기간에 데이터가 없습니다.")
    st.stop()

# Check MA data availability
missing_ma = [label for label in ma_windows if chart_df[label].dropna().empty]
if missing_ma:
    st.warning(
        f"데이터 부족으로 다음 이동평균선을 표시할 수 없습니다: {', '.join(missing_ma)}"
    )

# ── Chart annotations data ──────────────────────────────────────────────────
close_series = chart_df["close_price"].dropna()
if close_series.empty:
    st.warning("종가 데이터가 없습니다.")
    st.stop()

max_idx = close_series.idxmax()
min_idx = close_series.idxmin()
latest_idx = close_series.index[-1]
max_val = close_series[max_idx]
min_val = close_series[min_idx]
latest_val = close_series[latest_idx]

sym_code = id_to_sym[chosen_id]
sym_name = id_to_nm[chosen_id]

# ── Main area ───────────────────────────────────────────────────────────────
title_col, theme_col = st.columns([6, 2])
with title_col:
    st.markdown(f"### 📈 이동평균분석 — {sym_name} ({sym_code})")
with theme_col:
    theme_choice: str = st.radio(
        "차트 배경",
        options=["Dark", "Light"],
        index=0 if st.session_state["chart_theme"] == "Dark" else 1,
        horizontal=True,
        key="ma_theme_radio",
    )
    st.session_state["chart_theme"] = theme_choice

# ── Plotly chart ────────────────────────────────────────────────────────────
t = CHART_THEMES[st.session_state["chart_theme"]]
fig = go.Figure()

# Price line (orange, thicker)
fig.add_trace(
    go.Scatter(
        x=chart_df.index,
        y=chart_df["close_price"],
        mode="lines",
        name=sym_name,
        line=dict(
            color=PRICE_LINE_STYLE["color"],
            width=PRICE_LINE_STYLE["width"],
            dash=PRICE_LINE_STYLE["dash"],
        ),
        connectgaps=False,
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "날짜: %{x|%Y-%m-%d}<br>"
            "%{y:,.2f}<extra></extra>"
        ),
    )
)

# MA lines (solid, thinner, different colors)
ma_labels_sorted = list(ma_windows.keys())
for i, label in enumerate(ma_labels_sorted):
    if chart_df[label].dropna().empty:
        continue
    style = MA_LINE_STYLES[i % len(MA_LINE_STYLES)]
    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df[label],
            mode="lines",
            name=label,
            line=dict(
                color=style["color"],
                width=style["width"],
                dash=style["dash"],
            ),
            connectgaps=False,
            hovertemplate=(
                "<b>%{fullData.name}</b><br>"
                "날짜: %{x|%Y-%m-%d}<br>"
                "%{y:,.2f}<extra></extra>"
            ),
        )
    )

# Latest price horizontal line (red dotted)
fig.add_hline(
    y=latest_val,
    line_dash="dot",
    line_color="#e74c3c",
    line_width=1,
    annotation_text=f"현재 {latest_val:,.2f}",
    annotation_position="right",
    annotation_font_color="#e74c3c",
    annotation_font_size=11,
)

# Max annotation
fig.add_annotation(
    x=max_idx, y=max_val,
    text=f"▲ 최고 {max_val:,.2f}<br>({max_idx.strftime('%Y-%m-%d')})",
    showarrow=True, arrowhead=2, arrowsize=1, arrowcolor=t["font_color"],
    font=dict(color=t["font_color"], size=10),
    bgcolor=t["hover_bg"], bordercolor=t["line_color"], borderwidth=1,
    ax=0, ay=-35,
)

# Min annotation
fig.add_annotation(
    x=min_idx, y=min_val,
    text=f"▼ 최저 {min_val:,.2f}<br>({min_idx.strftime('%Y-%m-%d')})",
    showarrow=True, arrowhead=2, arrowsize=1, arrowcolor=t["font_color"],
    font=dict(color=t["font_color"], size=10),
    bgcolor=t["hover_bg"], bordercolor=t["line_color"], borderwidth=1,
    ax=0, ay=35,
)

# Quarter tick marks
quarters = pd.date_range(start=from_date, end=to_date, freq="QS")
tick_vals = quarters.tolist()
tick_text = [f"{d.year}-{(d.month - 1) // 3 + 1}Q" for d in quarters]

fig.update_layout(
    paper_bgcolor=t["paper_bgcolor"],
    plot_bgcolor=t["plot_bgcolor"],
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
        tickmode="array",
        tickvals=tick_vals,
        ticktext=tick_text,
        title=dict(
            text="날짜",
            standoff=12,
            font=dict(color=t["font_color"]),
        ),
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor=t["grid_color"],
        linecolor=t["line_color"],
        tickfont=dict(color=t["font_color"]),
        title=dict(
            text="종가/지표",
            standoff=10,
            font=dict(color=t["font_color"]),
        ),
        hoverformat=",.2f",
        tickformat=",",
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
    use_container_width=True,
    config=dict(
        responsive=True,
        displayModeBar=True,
        modeBarButtonsToRemove=["select2d", "lasso2d"],
        displaylogo=False,
        toImageButtonOptions=dict(format="png", filename="finsight_ma_chart", scale=2),
    ),
)

# ── Market Summary ──────────────────────────────────────────────────────────
st.divider()

short_result = compute_short_term_summary(df, "close_price", ma_windows)
long_result = compute_long_term_outlook(df, "close_price", ma_windows)

col_short, col_long = st.columns(2)

with col_short:
    st.markdown("##### 📊 단기(3개월) 시장 레러티브")
    st.markdown(
        f"<div style='font-size:0.85rem;line-height:1.7;padding:8px 12px;"
        f"border-radius:8px;background:rgba(255,255,255,0.03);"
        f"border:1px solid rgba(255,255,255,0.08)'>"
        f"{short_result['summary_text'].replace(chr(10), '<br>')}"
        f"</div>",
        unsafe_allow_html=True,
    )

with col_long:
    st.markdown("##### 🔭 중장기(1~10년) 전망")
    outlook_icon = long_result["outlook_icon"]
    outlook_label = long_result["outlook_label"]
    outlook_level = long_result["outlook_level"]

    level_bar = ""
    for i, item in enumerate(OUTLOOK_ICONS):
        if i == outlook_level:
            level_bar += f"<span style='font-size:1.3rem'>{item['icon']}</span> "
        else:
            level_bar += f"<span style='font-size:0.9rem;opacity:0.3'>{item['icon']}</span> "

    st.markdown(
        f"<div style='font-size:0.85rem;line-height:1.7;padding:8px 12px;"
        f"border-radius:8px;background:rgba(255,255,255,0.03);"
        f"border:1px solid rgba(255,255,255,0.08)'>"
        f"<div style='margin-bottom:6px;font-size:1rem;font-weight:600'>"
        f"장기 추세: {level_bar}"
        f"<span style='font-size:0.85rem;margin-left:4px'>{outlook_label}</span></div>"
        f"{long_result['summary_text'].replace(chr(10), '<br>')}"
        f"</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── CSV download ────────────────────────────────────────────────────────────
csv_cols = ["close_price"] + [l for l in ma_windows if l in chart_df.columns]
csv_df = chart_df[csv_cols].copy()
csv_df.index = csv_df.index.strftime("%Y-%m-%d")
csv_df.index.name = "날짜"
csv_df = csv_df.rename(columns={"close_price": sym_name})
csv_df = csv_df.reset_index()

st.download_button(
    label="📥 CSV 다운로드",
    data=csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"finsight_ma_{sym_code}.csv",
    mime="text/csv",
)
