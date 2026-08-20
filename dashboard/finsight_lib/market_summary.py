"""시장 요약 분석 — 단기 레러티브 및 중장기 전망 산출."""

from __future__ import annotations

import pandas as pd


# 5단계 이모티콘 정의 (매우긍정 → 매우부정)
OUTLOOK_ICONS: list[dict[str, str]] = [
    {"icon": "🟢🟢", "label": "매우 긍정적"},
    {"icon": "🟢",   "label": "긍정적"},
    {"icon": "🟡",   "label": "중립"},
    {"icon": "🔴",   "label": "부정적"},
    {"icon": "🔴🔴", "label": "매우 부정적"},
]


def _pct_change(current: float, reference: float) -> float:
    """변화율(%) 계산. reference가 0이면 0 반환."""
    if reference == 0:
        return 0.0
    return (current - reference) / abs(reference) * 100.0


def _trend_slope_score(series: pd.Series, window: int = 20) -> float:
    """최근 window 기간의 선형회귀 기울기를 정규화한 점수(-100~+100)."""
    if len(series.dropna()) < window:
        return 0.0
    recent = series.dropna().tail(window)
    x = range(len(recent))
    x_mean = sum(x) / len(x)
    y_mean = recent.mean()
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, recent))
    denominator = sum((xi - x_mean) ** 2 for xi in x)
    if denominator == 0:
        return 0.0
    slope = numerator / denominator
    return slope / y_mean * 100.0 * len(recent)


def compute_short_term_summary(
    df: pd.DataFrame,
    close_col: str = "close_price",
    ma_windows: dict[str, int] | None = None,
) -> dict:
    """단기(3개월 이내) 레러티브 분석 결과를 딕셔너리로 반환.

    Args:
        df: DatetimeIndex, close_col 포함. MA 컬럼이 있으면 활용.
        close_col: 종가 컬럼명.
        ma_windows: {"MA3M": 60, ...} MA label -> window 매핑.

    Returns:
        dict with keys: pct_1w, pct_1m, pct_3m, ma_position, trend_direction,
                        momentum, summary_text
    """
    close = df[close_col].dropna()
    if close.empty:
        return {"summary_text": "데이터가 부족하여 분석할 수 없습니다."}

    latest = close.iloc[-1]
    result: dict = {"latest": latest}

    # 1주/1개월/3개월 변화율
    for label, days in [("1주", 5), ("1개월", 20), ("3개월", 60)]:
        if len(close) > days:
            ref = close.iloc[-(days + 1)]
            result[f"pct_{label}"] = _pct_change(latest, ref)
        else:
            result[f"pct_{label}"] = None

    # MA 대비 위치 분석
    ma_positions: list[str] = []
    if ma_windows:
        for label, window in sorted(ma_windows.items(), key=lambda x: x[1]):
            if label in df.columns:
                ma_val = df[label].dropna()
                if not ma_val.empty:
                    ma_latest = ma_val.iloc[-1]
                    diff_pct = _pct_change(latest, ma_latest)
                    direction = "위" if diff_pct > 0 else "아래"
                    ma_positions.append(
                        f"{label} 대비 {abs(diff_pct):.1f}% {direction}"
                    )
    result["ma_positions"] = ma_positions

    # 추세 방향 (20일 기울기)
    slope = _trend_slope_score(close, window=min(20, len(close)))
    if slope > 2.0:
        result["trend_direction"] = "상승 추세"
    elif slope < -2.0:
        result["trend_direction"] = "하락 추세"
    else:
        result["trend_direction"] = "횡보(보합)"

    # 모멘텀 (최근 5일 vs 이전 5일 평균 비교)
    if len(close) >= 10:
        recent_5 = close.iloc[-5:].mean()
        prev_5 = close.iloc[-10:-5].mean()
        mom_pct = _pct_change(recent_5, prev_5)
        if mom_pct > 1.0:
            result["momentum"] = "가속 상승"
        elif mom_pct < -1.0:
            result["momentum"] = "가속 하락"
        else:
            result["momentum"] = "모멘텀 약화(둔화)"
    else:
        result["momentum"] = "판단 불가"

    # 요약 텍스트 생성
    parts: list[str] = []
    parts.append(f"▸ 현재가: {latest:,.2f}")

    pct_items = []
    for label in ["1주", "1개월", "3개월"]:
        val = result.get(f"pct_{label}")
        if val is not None:
            sign = "+" if val >= 0 else ""
            pct_items.append(f"{label} {sign}{val:.1f}%")
    if pct_items:
        parts.append(f"▸ 최근 수익률: {' / '.join(pct_items)}")

    parts.append(f"▸ 단기 추세: {result['trend_direction']}, {result['momentum']}")

    if ma_positions:
        parts.append(f"▸ 이동평균 대비: {', '.join(ma_positions)}")

    # 종합 판단
    pct_3m = result.get("pct_3개월")
    if pct_3m is not None:
        if pct_3m > 5:
            conclusion = "단기적으로 강세 흐름이 지속되고 있으며, 상대적 우위가 확인됩니다."
        elif pct_3m > 0:
            conclusion = "단기적으로 소폭 상승세를 보이며 안정적인 흐름입니다."
        elif pct_3m > -5:
            conclusion = "단기적으로 소폭 약세 또는 조정 구간에 진입한 모습입니다."
        else:
            conclusion = "단기적으로 뚜렷한 약세 흐름을 보이며, 주의가 필요합니다."
        parts.append(f"▸ 종합: {conclusion}")

    result["summary_text"] = "\n".join(parts)
    return result


def compute_long_term_outlook(
    df: pd.DataFrame,
    close_col: str = "close_price",
    ma_windows: dict[str, int] | None = None,
) -> dict:
    """중장기(1~10년) 전망 분석 결과를 딕셔너리로 반환.

    Args:
        df: 전체 기간 데이터(DatetimeIndex, close_col 포함).
        close_col: 종가 컬럼명.
        ma_windows: MA label -> window 매핑.

    Returns:
        dict with keys: pct_1y, pct_3y, pct_5y, long_trend, volatility,
                        outlook_level(0~4), outlook_icon, outlook_label,
                        summary_text
    """
    close = df[close_col].dropna()
    if close.empty:
        return {
            "outlook_level": 2,
            "outlook_icon": OUTLOOK_ICONS[2]["icon"],
            "outlook_label": OUTLOOK_ICONS[2]["label"],
            "summary_text": "데이터가 부족하여 중장기 전망을 산출할 수 없습니다.",
        }

    latest = close.iloc[-1]
    result: dict = {"latest": latest}
    score = 0.0
    score_factors = 0

    # 1년/3년/5년/10년 변화율
    for label, days in [("1년", 250), ("3년", 750), ("5년", 1250), ("10년", 2500)]:
        if len(close) > days:
            ref = close.iloc[-(days + 1)]
            pct = _pct_change(latest, ref)
            result[f"pct_{label}"] = pct
        else:
            result[f"pct_{label}"] = None

    # 장기 추세 점수 산출
    # Factor 1: 1년 수익률 기반
    pct_1y = result.get("pct_1년")
    if pct_1y is not None:
        score_factors += 1
        if pct_1y > 15:
            score += 2
        elif pct_1y > 5:
            score += 1
        elif pct_1y > -5:
            score += 0
        elif pct_1y > -15:
            score -= 1
        else:
            score -= 2

    # Factor 2: 3년 수익률 기반
    pct_3y = result.get("pct_3년")
    if pct_3y is not None:
        score_factors += 1
        if pct_3y > 30:
            score += 2
        elif pct_3y > 10:
            score += 1
        elif pct_3y > -10:
            score += 0
        elif pct_3y > -30:
            score -= 1
        else:
            score -= 2

    # Factor 3: 장기 이동평균 대비 현재가 위치
    if ma_windows:
        long_mas = {k: v for k, v in ma_windows.items() if v >= 250}
        if long_mas:
            above_count = 0
            total_count = 0
            for label in long_mas:
                if label in df.columns:
                    ma_val = df[label].dropna()
                    if not ma_val.empty:
                        total_count += 1
                        if latest > ma_val.iloc[-1]:
                            above_count += 1
            if total_count > 0:
                score_factors += 1
                ratio = above_count / total_count
                if ratio >= 1.0:
                    score += 2
                elif ratio >= 0.5:
                    score += 1
                elif ratio > 0:
                    score -= 1
                else:
                    score -= 2

    # Factor 4: 장기 추세 기울기 (250일)
    if len(close) >= 250:
        long_slope = _trend_slope_score(close, window=250)
        score_factors += 1
        if long_slope > 5:
            score += 2
        elif long_slope > 1:
            score += 1
        elif long_slope > -1:
            score += 0
        elif long_slope > -5:
            score -= 1
        else:
            score -= 2

    # 종합 점수 → 5단계 변환
    if score_factors > 0:
        avg_score = score / score_factors
    else:
        avg_score = 0.0

    if avg_score > 1.2:
        level = 0
    elif avg_score > 0.3:
        level = 1
    elif avg_score > -0.3:
        level = 2
    elif avg_score > -1.2:
        level = 3
    else:
        level = 4

    result["outlook_level"] = level
    result["outlook_icon"] = OUTLOOK_ICONS[level]["icon"]
    result["outlook_label"] = OUTLOOK_ICONS[level]["label"]

    # 장기 변동성 (연율화)
    if len(close) >= 250:
        returns = close.pct_change().dropna().tail(250)
        vol = returns.std() * (250 ** 0.5) * 100
        result["volatility"] = vol
        if vol > 30:
            vol_text = "높음"
        elif vol > 15:
            vol_text = "보통"
        else:
            vol_text = "낮음"
        result["volatility_text"] = vol_text
    else:
        result["volatility"] = None
        result["volatility_text"] = "산출 불가"

    # 요약 텍스트 생성
    parts: list[str] = []

    pct_items = []
    for label in ["1년", "3년", "5년", "10년"]:
        val = result.get(f"pct_{label}")
        if val is not None:
            sign = "+" if val >= 0 else ""
            pct_items.append(f"{label} {sign}{val:.1f}%")
    if pct_items:
        parts.append(f"▸ 장기 수익률: {' / '.join(pct_items)}")

    if result.get("volatility") is not None:
        parts.append(
            f"▸ 연간 변동성: {result['volatility']:.1f}% ({result['volatility_text']})"
        )

    # 장기 추세 해석
    if level == 0:
        trend_text = "장기적으로 뚜렷한 상승 추세가 확인되며, 구조적 강세가 지속되고 있습니다."
    elif level == 1:
        trend_text = "장기적으로 완만한 상승 흐름을 보이고 있어 긍정적인 국면입니다."
    elif level == 2:
        trend_text = "장기 추세가 뚜렷하지 않으며, 방향성 탐색 구간에 있습니다."
    elif level == 3:
        trend_text = "장기적으로 하락 압력이 존재하며, 회복에 시간이 필요할 수 있습니다."
    else:
        trend_text = "장기적으로 구조적 약세가 지속되고 있어 주의가 필요합니다."

    parts.append(f"▸ 전망: {trend_text}")
    result["summary_text"] = "\n".join(parts)
    return result
