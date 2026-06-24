"""시장지표트랜드 — 다중 지표 비교 차트 (Home)."""

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from services.connection import get_engine          # noqa: F401 – triggers secrets bridge
from services.price_service import get_series, list_symbol_coverage
from services.symbol_service import list_symbols
from finsight_lib.palette import CHART_THEMES, COLOR_EMOJI, COLOR_MAP, RAINBOW, RAINBOW_NAMES
from finsight_lib.periods import DEFAULT_PRESET, DIRECT_LABEL, PRESETS, from_date_by_preset
from finsight_lib.transform import normalize_100, to_wide

_MAX_SELECT    = 10
_DEFAULT_CODES = ["KS11", "KQ11", "US500", "VIX"]
_MS_KEY        = "ms_symbols"


# ─── Cached loaders ───────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def _load_symbols() -> list[dict]:
    return list_symbols()


# ─── Symbol master data ───────────────────────────────────────────────────────
all_syms = _load_symbols()
if not all_syms:
    st.error(
        "\uc885\ubaa9 \uc815\ubcf4\ub97c \ubd88\ub7ec\uc62c \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. "
        "DB \uc5f0\uacb0 \ubc0f \uc2dc\ub4dc \ub4f1\ub85d\uc744 \ud655\uc778\ud558\uc138\uc694."
    )
    st.stop()

all_ids:     list[int]       = [s["symbol_id"]  for s in all_syms]
id_to_nm:    dict[int, str]  = {s["symbol_id"]: s["symbol_nm"] for s in all_syms}
id_to_sym:   dict[int, str]  = {s["symbol_id"]: s["symbol"]    for s in all_syms}
code_to_id:  dict[str, int]  = {s["symbol"]:    s["symbol_id"] for s in all_syms}
default_ids: list[int]       = [code_to_id[c] for c in _DEFAULT_CODES if c in code_to_id]


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
        + "<th>Symbol</th><th>\uc9c0\ud45c\uba85</th>"
        + "<th>From</th><th>To</th><th class='num'>\uac74\uc218</th>"
        + "</tr></thead>"
        + f"<tbody>{body}</tbody>"
        + "</table>"
    )


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── 1. Symbol multiselect ──────────────────────────────────────────────────
    n_sel = len(st.session_state[_MS_KEY])
    st.markdown(
        f"#### \uc2dc\uc7a5\uc9c0\ud45c \uc120\ud0dd &nbsp; `{n_sel} / {_MAX_SELECT}`",
        unsafe_allow_html=True,
    )

    bc1, bc2, bc3 = st.columns(3)
    if bc1.button("\uc804\uccb4", use_container_width=True):
        st.session_state[_MS_KEY] = list(all_ids[:_MAX_SELECT])
    if bc2.button("\ud574\uc81c", use_container_width=True):
        st.session_state[_MS_KEY] = []
    if bc3.button("\uae30\ubcf8\uac12", use_container_width=True):
        st.session_state[_MS_KEY] = list(default_ids)

    selected_ids: list[int] = st.multiselect(
        "\uc9c0\ud45c \uc120\ud0dd",
        options=all_ids,
        key=_MS_KEY,
        format_func=lambda sid: f"{id_to_sym[sid]} \u2014 {id_to_nm[sid]}",
        max_selections=_MAX_SELECT,
        label_visibility="collapsed",
        placeholder="\uc9c0\ud45c\ub97c \uc120\ud0dd\ud558\uc138\uc694 (\ucd5c\ub300 10\uac1c)",
    )

    # ── 2. Color assignment ────────────────────────────────────────────────────
    if selected_ids:
        _init_colors(selected_ids)
        st.markdown(
            "<div style='font-size:0.78rem;font-weight:600;margin:6px 0 2px'>"
            "\uc9c0\ud45c\ubcc4 \uc0c9\uc0c1 \uc9c0\uc815</div>",
            unsafe_allow_html=True,
        )
        for sid in selected_ids:
            color_name = st.session_state.get(f"cs_{sid}", RAINBOW_NAMES[0])
            emoji      = COLOR_EMOJI.get(color_name, "\u26aa")
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
    st.markdown("#### \uae30\uac04 \uc124\uc815")
    to_date: date = st.date_input("\uc885\ub8cc\uc77c", value=date.today())
    preset: str = st.selectbox(
        "\uae30\uac04 \ud504\ub9ac\uc14b",
        options=PRESETS,
        index=PRESETS.index(DEFAULT_PRESET),
        key="period_preset",
    )
    if preset == DIRECT_LABEL:
        try:
            default_from = to_date.replace(year=to_date.year - 1)
        except ValueError:
            default_from = to_date.replace(year=to_date.year - 1, day=28)
        from_date: date = st.date_input("\uc2dc\uc791\uc77c", value=default_from)
    else:
        from_date = from_date_by_preset(to_date, preset)
        st.caption(f"\uc2dc\uc791\uc77c: {from_date.strftime('%Y-%m-%d')}")

    if from_date > to_date:
        st.error("\uc2dc\uc791\uc77c\uc774 \uc885\ub8cc\uc77c\ubcf4\ub2e4 \ud074 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.")
        from_date = to_date

    st.divider()

    # ── 4. Display mode ────────────────────────────────────────────────────────
    st.markdown("#### \ud45c\uc2dc \ubc29\uc2dd")
    normalize: bool = st.toggle(
        "\uc815\uaddc\ud654 (\uae30\uc900 100)",
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

    # ── 5. Reference coverage table + Refresh ─────────────────────────────────
    hdr_col, btn_col = st.columns([8, 1])
    hdr_col.markdown(
        "<div style='font-size:0.78rem;font-weight:600;margin-bottom:4px'>"
        "\uc9c0\ud45c \ub370\uc774\ud130 \ubcf4\uc720\ud604\ud669</div>",
        unsafe_allow_html=True,
    )
    if btn_col.button("\U0001f504", help="\ubcf4\uc720\ud604\ud669 \ubc0f \uc9c0\ud45c \ubaa9\ub85d \uac31\uc2e0"):
        list_symbol_coverage.clear()
        _load_symbols.clear()
        st.rerun()

    try:
        cov_list = list_symbol_coverage()
        cov_map  = {c["symbol_id"]: c for c in cov_list}
    except Exception:
        cov_map  = {}

    st.markdown(_coverage_table_html(all_syms, cov_map), unsafe_allow_html=True)


# ─── Main area ────────────────────────────────────────────────────────────────
title_col, theme_col = st.columns([6, 2])
with title_col:
    st.markdown("### \U0001f4c8 FinSight \ub300\uc2dc\ubcf4\ub4dc")
with theme_col:
    theme_choice: str = st.radio(
        "\ucc28\ud2b8 \ubc30\uacbd",
        options=["Dark", "Light"],
        index=0 if st.session_state["chart_theme"] == "Dark" else 1,
        horizontal=True,
        key="chart_theme_radio",
    )
    st.session_state["chart_theme"] = theme_choice

if not selected_ids:
    st.info(
        "\uc88c\uce21 \uc0ac\uc774\ub4dc\ubc14\uc5d0\uc11c "
        "\uc9c0\ud45c\ub97c \uc120\ud0dd\ud558\uba74 \ucc28\ud2b8\uac00 \ud45c\uc2dc\ub429\ub2c8\ub2e4."
    )
    st.stop()

# ─── Fetch data ───────────────────────────────────────────────────────────────
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
            text="\ub0a0\uc9dc",
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
csv_df.index.name = "\ub0a0\uc9dc"
csv_df = csv_df.reset_index()

st.download_button(
    label="\U0001f4e5 CSV \ub2e4\uc6b4\ub85c\ub4dc",
    data=csv_df.to_csv(index=False).encode("utf-8-sig"),
    file_name="finsight_chart.csv",
    mime="text/csv",
)
