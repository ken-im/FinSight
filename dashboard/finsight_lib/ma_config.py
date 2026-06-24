"""Moving average configuration constants."""

from __future__ import annotations

MA_OPTIONS: dict[str, dict] = {
    "5\uc77c":         {"window": 5,   "label": "MA5D"},
    "10\uc77c":        {"window": 10,  "label": "MA10D"},
    "1\uac1c\uc6d4":  {"window": 20,  "label": "MA1M"},
    "3\uac1c\uc6d4":  {"window": 60,  "label": "MA3M"},
    "6\uac1c\uc6d4":  {"window": 125, "label": "MA6M"},
    "1\ub144":         {"window": 250, "label": "MA1Y"},
    "2\ub144":         {"window": 500, "label": "MA2Y"},
    "3\ub144":         {"window": 750, "label": "MA3Y"},
}

MA_OPTION_NAMES: list[str] = list(MA_OPTIONS.keys())

MA_DEFAULTS: list[str] = ["5\uc77c", "10\uc77c", "3\uac1c\uc6d4"]

MA_LINE_STYLES: list[dict] = [
    {"dash": "solid", "width": 1, "color": "#ff6b6b"},
    {"dash": "solid", "width": 1, "color": "#5dd0f5"},
    {"dash": "solid", "width": 1, "color": "#7ee787"},
]

PRICE_LINE_STYLE: dict = {
    "dash": "solid", "width": 2.5, "color": "#ffa726",
}
