"""\uc774\ub3d9\ud3c9\uade0\ubd84\uc11d \u2014 \ub2e8\uc77c \uc9c0\ud45c SMA \ucc28\ud2b8."""

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


@st.cache_data(ttl=86400, show_spinner=False)
def _load_symbols() -> list[dict]:
    return list_symbols()


symbols = _load_symbols()
if not symbols:
    st.info(
        "\ub4f1\ub85d\ub41c \uc885\ubaa9\uc774 \uc5c6\uc2b5\ub2c8\ub2e4. "
        "\uba3c\uc800 \uc885\ubaa9\ub9c8\uc2a4\ud130\uc5d0\uc11c \uc885\ubaa9\uc744 \ub4f1\ub85d\ud558\uc138\uc694."
    )
    st.stop()

id_to_nm:  dict[int, str] = {s["symbol_id"]: s["symbol_nm"] for s in symbols}
id_to_sym: dict[int, str] = {s["symbol_id"]: s["symbol"]    for s in symbols}

if "chart_theme" not in st.session_state:
    st.session_state["chart_theme"] = "Dark"

# \u2500\u2500 Sidebar \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
with st.sidebar:
    # 1. Symbol select (single)
    st.markdown("#### \uc2dc\uc7a5\uc9c0\ud45c \uc120\ud0dd")
    sym_options = {
        f'{s["symbol"]} \u2014 {s["symbol_nm"]}': s["symbol_id"]
        for s in symbols
    }
    sym_labels = list(sym_options.keys())
    chosen_label = st.selectbox(
        "\uc9c0\ud45c \uc120\ud0dd",
        sym_labels,
        key="ma_symbol",
        label_visibility="collapsed",
    )
    chosen_id = sym_options[chosen_label]

    st.divider()

    # 2. Period settings (reuse periods.py)
    st.markdown("#### \uae30\uac04 \uc124\uc815")
    to_date: date = st.date_input("\uc885\ub8cc\uc77c", value=date.today(), key="ma_to")
    preset: str = st.selectbox(
        "\uae30\uac04 \ud504\ub9ac\uc14b",
        options=PRESETS,
        index=PRESETS.index(DEFAULT_PRESET),
        key="ma_preset",
    )
    if preset == DIRECT_LABEL:
        try:
            default_from = to_date.replace(year=to_date.year - 1)
        except ValueError:
            default_from = to_date.replace(year=to_date.year - 1, day=28)
        from_date: date = st.date_input("\uc2dc\uc791\uc77c", value=default_from, min_value=date(1990, 1, 2), key="ma_from")
    else:
        from_date = from_date_by_preset(to_date, preset)
        st.caption(f"\uc2dc\uc791\uc77c: {from_date.strftime('%Y-%m-%d')}")

    if from_date > to_date:
        st.error("\uc2dc\uc791\uc77c\uc774 \uc885\ub8cc\uc77c\ubcf4\ub2e4 \ud074 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
        from_date = to_date

    st.divider()

    # 3. MA line settings
    st.markdown("#### \uc774\ub3d9\ud3c9\uade0\uc120 \uc124\uc815")
    ma_selections: list[str] = []
    for i in range(3):
        default_idx = MA_OPTION_NAMES.index(MA_DEFAULTS[i]) if MA_DEFAULTS[i] in MA_OPTION_NAMES else 0
        sel = st.selectbox(
            f"\uc774\ub3d9\ud3c9\uade0 {i + 1}",
            options=MA_OPTION_NAMES,
            index=default_idx,
            key=f"ma_sel_{i}",
        )
        opt = MA_OPTIONS[sel]
        st.caption(f"  {opt['label']}, {opt['window']}\uc77c")
        ma_selections.append(sel)

# \u2500\u2500 Data fetch with buffer \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
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
    st.error(f"\ub370\uc774\ud130 \uc870\ud68c \uc624\ub958: {exc}")
    st.stop()

if not rows_data:
    st.warning(
        f"\uc120\ud0dd\ud55c \uae30\uac04\uc5d0 \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4."
    )
    st.stop()

# \u2500\u2500 Build DataFrame + SMA \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
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
    st.warning("\ud45c\uc2dc \uae30\uac04\uc5d0 \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.")
    st.stop()

# Check MA data availability
missing_ma = [label for label in ma_windows if chart_df[label].dropna().empty]
if missing_ma:
    st.warning(
        f"\ub370\uc774\ud130 \ubd80\uc871\uc73c\ub85c \ub2e4\uc74c \uc774\ub3d9\ud3c9\uade0\uc120\uc744 \ud45c\uc2dc\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4: {', '.join(missing_ma)}"
    )

# \u2500\u2500 Chart annotations data \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
close_series = chart_df["close_price"].dropna()
if close_series.empty:
    st.warning("\uc885\uac00 \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.")
    st.stop()

max_idx = close_series.idxmax()
min_idx = close_series.idxmin()
latest_idx = close_series.index[-1]
max_val = close_series[max_idx]
min_val = close_series[min_idx]
latest_val = close_series[latest_idx]

sym_code = id_to_sym[chosen_id]
sym_name = id_to_nm[chosen_id]

# \u2500\u2500 Main area \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
title_col, theme_col = st.columns([6, 2])
with title_col:
    st.markdown(f"### \U0001f4c8 \uc774\ub3d9\ud3c9\uade0\ubd84\uc11d \u2014 {sym_name} ({sym_code})")
with theme_col:
    theme_choice: str = st.radio(
        "\ucc28\ud2b8 \ubc30\uacbd",
        options=["Dark", "Light"],
        index=0 if st.session_state["chart_theme"] == "Dark" else 1,
        horizontal=True,
        key="ma_theme_radio",
    )
    st.session_state["chart_theme"] = theme_choice

# \u2500\u2500 Plotly chart \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
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
            "\ub0a0\uc9dc: %{x|%Y-%m-%d}<br>"
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
                "\ub0a0\uc9dc: %{x|%Y-%m-%d}<br>"
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
    annotation_text=f"\ud604\uc7ac {latest_val:,.2f}",
    annotation_position="right",
    annotation_font_color="#e74c3c",
    annotation_font_size=11,
)

# Max annotation
fig.add_annotation(
    x=max_idx, y=max_val,
    text=f"\u25b2 \ucd5c\uace0 {max_val:,.2f}<br>({max_idx.strftime('%Y-%m-%d')})",
    showarrow=True, arrowhead=2, arrowsize=1, arrowcolor=t["font_color"],
    font=dict(color=t["font_color"], size=10),
    bgcolor=t["hover_bg"], bordercolor=t["line_color"], borderwidth=1,
    ax=0, ay=-35,
)

# Min annotation
fig.add_annotation(
    x=min_idx, y=min_val,
    text=f"\u25bc \ucd5c\uc800 {min_val:,.2f}<br>({min_idx.strftime('%Y-%m-%d')})",
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
            text="\ub0a0\uc9dc",
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
            text="\uc885\uac00/\uc9c0\ud45c",
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

# \u2500\u2500 CSV download \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
csv_cols = ["close_price"] + [l for l in ma_windows if l in chart_df.columns]
csv_df = chart_df[csv_cols].copy()
csv_df.index = csv_df.index.strftime("%Y-%m-%d")
csv_df.index.name = "\ub0a0\uc9dc"
csv_df = csv_df.rename(columns={"close_price": sym_name})
csv_df = csv_df.reset_index()

st.download_button(
    label="\U0001f4e5 CSV \ub2e4\uc6b4\ub85c\ub4dc",
    data=csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"finsight_ma_{sym_code}.csv",
    mime="text/csv",
)
