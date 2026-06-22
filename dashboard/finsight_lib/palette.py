"""Color palette and chart theme definitions."""

from __future__ import annotations

# English name -> hex (15 colors, rainbow order)
COLOR_MAP: dict[str, str] = {
    "Red":       "#e74c3c",
    "Orange":    "#e67e22",
    "Yellow":    "#f1c40f",
    "Green":     "#2ecc71",
    "Blue":      "#3498db",
    "Navy":      "#4834d4",
    "Purple":    "#9b59b6",
    "Sky Blue":  "#4e9af1",
    "Apricot":   "#f1a34e",
    "Lime":      "#6af178",
    "Teal":      "#1abc9c",
    "Gold":      "#f39c12",
    "Lavender":  "#a78bfa",
    "Crimson":   "#f14e4e",
    "Gray":      "#95a5a6",
}

RAINBOW_NAMES: list[str] = list(COLOR_MAP.keys())   # English names for SelectboxColumn
RAINBOW:       list[str] = list(COLOR_MAP.values()) # hex codes for chart traces

# Approximate colored circle emoji per color name
COLOR_EMOJI: dict[str, str] = {
    "Red":       "🔴",
    "Orange":    "🟠",
    "Yellow":    "🟡",
    "Green":     "🟢",
    "Blue":      "🔵",
    "Navy":      "🔵",
    "Purple":    "🟣",
    "Sky Blue":  "🔵",
    "Apricot":   "🟠",
    "Lime":      "🟢",
    "Teal":      "🟢",
    "Gold":      "🟡",
    "Lavender":  "🟣",
    "Crimson":   "🔴",
    "Gray":      "⚫",
}

# Bloomberg-style chart themes
CHART_THEMES: dict[str, dict[str, str]] = {
    "Dark": {
        "paper_bgcolor": "#0d1117",
        "plot_bgcolor":  "#0d1117",
        "font_color":    "#e6edf3",
        "grid_color":    "#2a2a2a",
        "line_color":    "#30363d",
        "slider_bg":     "#161b22",
        "legend_bg":     "rgba(13,17,23,0.85)",
        "hover_bg":      "#161b22",
        "hover_font":    "#e6edf3",
    },
    "Light": {
        "paper_bgcolor": "#ffffff",
        "plot_bgcolor":  "#f8f9fa",
        "font_color":    "#1f1f1f",
        "grid_color":    "#e0e0e0",
        "line_color":    "#cccccc",
        "slider_bg":     "#e8e8e8",
        "legend_bg":     "rgba(255,255,255,0.9)",
        "hover_bg":      "#ffffff",
        "hover_font":    "#1f1f1f",
    },
}
