# FinSight 대시보드 V2 실행 계획 (PLAN-front-20260624)

> 본 문서는 [PRD-front-20260624](./PRD-front-20260624.md)를 구현하기 위한 실행 계획이다.
> 기존 [PLAN-front-20260622](./PLAN-front-20260622.md)에서 완성된 대시보드를 기반으로,
> **메뉴 개편**, **이동평균분석 신규 페이지**, **시장지표일별시세 전환**, **보유현황 Refresh 버튼**을 추가한다.
> `reference/fx_trend` 디렉토리는 `.gitignore` 대상이므로 PRD 본문 스펙을 기준으로 구현한다.

---

## 1. 목표

- 좌측 패널 메뉴를 **시장지표트랜드 → 이동평균분석 → 시장지표일별시세 → Admin Symbols** 순서로 개편한다.
- 단일 시장지표에 대한 **이동평균(SMA) 분석 차트** 페이지를 신규 구현한다.
- 기존 관리자 종가내역 조회를 **시장지표일별시세**(일반 화면)로 전환한다.
- 지표데이터 보유현황에 **Refresh 버튼**을 추가하여 캐시를 갱신한다.

---

## 2. 범위

### 2.1. 포함 (In Scope)

| 영역 | 기능 (PRD 기준) |
| --- | --- |
| 메뉴 개편 | `st.navigation()` API로 전환. 파일 기반 `pages/` → `views/` 구조로 변경 |
| 시장지표트랜드 | 기존 `app.py` 차트 로직을 `views/market_trend.py`로 분리. 기능 변경 없음 |
| 이동평균분석 (신규) | 단일 지표 선택, SMA 3개선 설정, 시계열+MA 중첩 차트, 최고/최저/최근 값 표시, 분기 X축 |
| 시장지표일별시세 (전환) | 기존 `2_admin_prices.py` 기반, 인증 제거, 기간 프리셋 추가 |
| Admin Symbols | 기존 `1_admin_symbols.py`를 `views/`로 이동, 인증 유지, 메뉴 하단 배치 |
| Refresh 버튼 | 보유현황 테이블 옆 🔄 아이콘 버튼, `st.cache_data` 선택적 클리어 |

### 2.2. 제외 (Out of Scope)

- 시장지표트랜드의 기존 기능 변경 (다중 선택, 정규화 등은 현행 유지)
- 신규 데이터 수집·적재 기능
- Streamlit Community Cloud 재배포 (별도 단계)

---

## 3. 아키텍처 변경: `st.navigation()` 전환

### 3.1. 전환 이유

| 항목 | 기존 (파일 기반 `pages/`) | 변경 (`st.navigation()`) |
| --- | --- | --- |
| 메뉴 순서 | 파일명 숫자 접두사로 결정 | `st.Page` 리스트 순서로 자유 제어 |
| 메뉴 라벨 | 파일명에서 자동 추출 (한글 파일명 → 인코딩 문제) | `title` 파라미터로 한글 라벨 지정 |
| 메뉴 그루핑 | 불가 | dict 키로 섹션 분리 (분석 / 관리) |
| 관리자 메뉴 숨김 | `st.page_link()`로 별도 링크 필요 | 하단 섹션으로 자연스럽게 배치 |
| `set_page_config` | 각 페이지마다 호출 | `app.py`에서 1회 호출 |

### 3.2. `app.py` 라우터 구조

```python
# dashboard/app.py (개편 후)
import streamlit as st

st.set_page_config(page_title="FinSight", page_icon="🏠", layout="wide")

# sys.path bootstrap (ROOT + DASH)
# ... (기존과 동일)

pg = st.navigation({
    "분석": [
        st.Page("views/market_trend.py", title="시장지표트랜드", icon="🏠", default=True),
        st.Page("views/ma_analysis.py",  title="이동평균분석",   icon="📈"),
        st.Page("views/daily_market.py", title="시장지표일별시세", icon="📋"),
    ],
    "관리": [
        st.Page("views/admin_symbols.py", title="Admin Symbols", icon="🗂️"),
    ],
})

pg.run()
```

- `sys.path` 부트스트랩은 `app.py`에서 1회 수행 → 모든 뷰에서 `from services.xxx`, `from finsight_lib.xxx`, `from src.db.xxx` 임포트 가능.
- 각 뷰 파일에서는 `st.set_page_config()` 호출하지 않음 (중복 호출 오류 방지).
- 각 뷰 파일의 sys.path 부트스트랩 코드도 제거 (app.py에서 처리).

---

## 4. 디렉토리 구조 (변경분)

```
dashboard/
├── app.py                          # [전면 변경] st.navigation() 라우터
├── views/                          # [신규] 페이지 뷰 디렉토리
│   ├── __init__.py
│   ├── market_trend.py             # [이동] 기존 app.py 차트 로직 → 시장지표트랜드
│   ├── ma_analysis.py              # [신규] 이동평균분석
│   ├── daily_market.py             # [신규] 기존 2_admin_prices 기반 → 시장지표일별시세
│   └── admin_symbols.py            # [이동] 기존 1_admin_symbols → views/ 이동
├── pages/                          # [삭제] st.navigation() 전환으로 불필요
│   ├── 1_admin_symbols.py          # → views/admin_symbols.py 로 이동 후 삭제
│   └── 2_admin_prices.py           # → views/daily_market.py 로 전환 후 삭제
├── services/
│   ├── connection.py               # (변경 없음)
│   ├── auth.py                     # (변경 없음)
│   ├── symbol_service.py           # (변경 없음)
│   └── price_service.py            # [확장] list_daily_prices() 추가
├── finsight_lib/
│   ├── __init__.py
│   ├── palette.py                  # [확장] MA_LINE_STYLES 추가
│   ├── periods.py                  # (변경 없음, 전 페이지에서 재사용)
│   ├── transform.py                # [확장] calc_sma() 추가
│   └── ma_config.py                # [신규] MA 설정 상수
└── __init__.py
```

---

## 5. 이동평균분석 상세 설계 (신규 페이지)

### 5.1. 조회 조건 (사이드바)

```
┌───────────────────────────────────────────────┐
│ #### 시장지표 선택                              │
│ ┌─────────────────────────────────────────┐    │
│ │ KS11 — KOSPI 지수                   ▼  │    │  ← st.selectbox (단일 선택)
│ └─────────────────────────────────────────┘    │
│                                               │
│ #### 기간 설정                                  │
│ 종료일: [2026-06-24]  프리셋: [1년 ▼]           │
│ 시작일: 2025-06-24                             │
│                                               │
│ #### 이동평균선 설정                              │
│ 이동평균 1: [3개월  ▼]  (MA3M, 60일)            │
│ 이동평균 2: [1년    ▼]  (MA1Y, 250일)           │
│ 이동평균 3: [3년    ▼]  (MA3Y, 750일)           │
└───────────────────────────────────────────────┘
```

- **시장지표 선택**: `st.selectbox` — `symbol_master` 전체 목록에서 1개 선택
- **기간 설정**: 시장지표트랜드와 동일한 프리셋 (`periods.py` 재사용)
- **이동평균선 3개**: 각각 `st.selectbox`로 기간 선택, 기본값 = 3개월, 1년, 3년

### 5.2. 이동평균 설정 상수 (`finsight_lib/ma_config.py`)

```python
MA_OPTIONS: dict[str, dict] = {
    "1개월":  {"window": 20,  "label": "MA1M"},
    "3개월":  {"window": 60,  "label": "MA3M"},
    "6개월":  {"window": 125, "label": "MA6M"},
    "1년":    {"window": 250, "label": "MA1Y"},
    "2년":    {"window": 500, "label": "MA2Y"},
    "3년":    {"window": 750, "label": "MA3Y"},
}

MA_DEFAULTS: list[str] = ["3개월", "1년", "3년"]  # 이동평균 1/2/3 기본값
```

| 설정 | 거래일 수 | 표시기호 | 산출 근거 |
| --- | --- | --- | --- |
| 1개월 | 20 | MA1M | 60 ÷ 3 = 20 |
| 3개월 | 60 | MA3M | PRD 명시 |
| 6개월 | 125 | MA6M | 250 ÷ 2 = 125 |
| 1년 | 250 | MA1Y | PRD 명시 |
| 2년 | 500 | MA2Y | 250 × 2 |
| 3년 | 750 | MA3Y | PRD 명시 |

### 5.3. 데이터 버퍼 전략

> PRD 3.3-5) "그래프 시작 시점의 이동평균 산출을 위하여 충분한 환율 데이터를 가져와서 시각화 한다."

- 선택된 3개 MA 중 최대 윈도우 크기를 구한다.
- 차트 시작일(from_date)에서 **최대 윈도우 × 1.5배**(휴장일 감안) 만큼 역산하여 데이터를 조회한다.
- SMA 계산 후, 차트에는 from_date ~ to_date 구간만 표시한다.

```python
max_window = max(MA_OPTIONS[sel]["window"] for sel in [ma1, ma2, ma3])
buffer_days = int(max_window * 1.5)
extended_from = from_date - timedelta(days=buffer_days)
```

### 5.4. SMA 계산 (`finsight_lib/transform.py` 확장)

```python
def calc_sma(
    df: pd.DataFrame,
    close_col: str,
    windows: dict[str, int],
) -> pd.DataFrame:
    """단순 이동평균(SMA) 계산.

    Args:
        df: DatetimeIndex, close_col 컬럼 포함.
        close_col: 종가 컬럼명.
        windows: {"MA3M": 60, "MA1Y": 250, ...} 형태.

    Returns:
        원본 + MA 컬럼이 추가된 DataFrame.
    """
    result = df.copy()
    for label, w in windows.items():
        result[label] = result[close_col].rolling(window=w, min_periods=w).mean()
    return result
```

### 5.5. 차트 설계

```
┌──────────────────────────────────────────────────────────┐
│ 📈 이동평균분석 — KOSPI 지수 (KS11)                       │
│                                                          │
│  Y축                              ▲ 최고 2,897.43       │
│  (종가)    ╭─╮                   (2026-03-14)           │
│           ╱   ╲    ╭──────╮                              │
│    ──────╱─────╲──╱───────╲────╱─────────── MA3M (실선)  │
│   ══════╱═══════╲╱═════════╲══╱════════════ MA1Y (실선)  │
│  ------╱---------╲----------╲╱------------- MA3Y (실선)  │
│       ╱            ╲         ╱                           │
│      ╱              ╰───────╯     현재 2,654.12          │
│  ·····················································   │ ← 현재가 수평선 (점선, 빨강)
│  ▼ 최저 2,312.88                                         │
│  (2025-08-22)                                            │
│  ─┬──────┬──────┬──────┬──────┬──────┬──────┬──── X축   │
│  2025-3Q 2025-4Q 2026-1Q 2026-2Q                        │
└──────────────────────────────────────────────────────────┘
```

#### X축 (날짜)
- 분기 간격 눈금: `ticktext` / `tickvals`로 `"YYYY-NQ"` 형식 수동 생성
  ```python
  quarters = pd.date_range(start=from_date, end=to_date, freq="QS")
  ticktext = [f"{d.year}-{(d.month - 1) // 3 + 1}Q" for d in quarters]
  ```

#### Y축 (종가/지표)
- 단일 지표이므로 원본 값 그대로 사용 (정규화 불필요)

#### 원본 데이터 라인
- `go.Scatter` (mode="lines"), 선택한 지표의 종가 시계열
- 색상: **오렌지 (`#e67e22`)**, 이동평균선보다 **1px 굵게** (width=2.8)
- 실선 스타일

#### 이동평균선 3개
- **모두 실선(solid)**, 선색으로 구분, 원본보다 1px 얇게 (width=1.8):
  ```python
  MA_LINE_STYLES: dict[int, dict] = {
      0: {"dash": "solid", "width": 1.8, "color": "#3498db"},  # 단기 MA (파랑)
      1: {"dash": "solid", "width": 1.8, "color": "#2ecc71"},  # 중기 MA (초록)
      2: {"dash": "solid", "width": 1.8, "color": "#9b59b6"},  # 장기 MA (보라)
  }
  PRICE_LINE_STYLE: dict = {"dash": "solid", "width": 2.8, "color": "#e67e22"}  # 원본 (오렌지)
  ```

#### 최고/최저/최근 표시
- `fig.add_annotation()` 으로 원본 종가 기준 최고점·최저점·최근 일자 값 표시
- **현재가 수평선**: `fig.add_hline(y=latest_price, line_dash="dot", line_color="#e74c3c")` — 빨간 점선으로 최근 종가 수준을 강조 + 우측에 값 라벨

#### 차트 테마
- 시장지표트랜드와 동일한 `CHART_THEMES` (Dark/Light) 적용

### 5.6. CSV 다운로드
- 시장지표트랜드와 동일하게 차트 데이터(원본 + MA값) CSV 다운로드 제공

---

## 6. 시장지표일별시세 설계 (전환 페이지)

### 6.1. 기존 대비 변경 사항

| 항목 | 기존 (`2_admin_prices.py`) | 변경 (`daily_market.py`) |
| --- | --- | --- |
| 인증 | `require_admin()` 필요 | **인증 없음** (일반 화면) |
| 메뉴 라벨 | "종가내역 조회" | "시장지표일별시세" |
| 지표 선택 | selectbox (전체 목록) | selectbox (단일 선택, 동일) |
| 기간 필터 | 없음 (전체 데이터 페이징) | **기간 프리셋 추가** (시장지표트랜드와 동일) |
| 페이지 위치 | 관리자 메뉴 | 일반 메뉴 (이동평균분석 아래) |
| 데이터 표시 | OHLCV + 등락률, 30행/페이지 | 동일 유지 |
| `set_page_config` | 페이지 내 호출 | 제거 (app.py에서 처리) |

### 6.2. 조회 조건

```
┌───────────────────────────────────────────┐
│ #### 시장지표 선택                          │
│ [KS11 — KOSPI 지수                   ▼]  │  ← st.selectbox
│                                           │
│ #### 기간 설정                              │
│ 종료일: [오늘]    프리셋: [1년 ▼]           │
│ 시작일: 2025-06-24                         │
└───────────────────────────────────────────┘
```

### 6.3. 데이터 서비스

기존 `list_prices()` 는 symbol_id + 페이지 기반. 기간 필터를 추가한 함수를 신규 작성:

```python
# price_service.py 확장
def list_daily_prices(
    symbol_id: int,
    from_dt: str,
    to_dt: str,
    page: int = 1,
    page_size: int = PAGE_SIZE,
) -> tuple[list[dict], int]:
    """기간 범위 내 일별시세 조회 (페이징). 반환: (rows, total_count)."""
```

---

## 7. 보유현황 Refresh 버튼

> PRD 4장: "지표데이터 보유현황에 refresh 버튼 추가하여 보유현황 및 시장지표 선택 드롭다운의 내용을 갱신"

### 7.1. 구현 방식

```python
# 보유현황 헤더 옆 Refresh 버튼
hdr_col, btn_col = st.columns([8, 1])
hdr_col.markdown("지표 데이터 보유현황")
if btn_col.button("🔄", help="보유현황 및 지표 목록 갱신"):
    list_symbol_coverage.clear()   # coverage 캐시 클리어
    _load_symbols.clear()          # symbol 목록 캐시 클리어
    st.rerun()
```

- `st.cache_data` 로 캐싱된 `list_symbol_coverage()` 와 `_load_symbols()` 의 캐시를 선택적으로 클리어.
- 클리어 후 `st.rerun()` 으로 페이지 리로드 → 최신 데이터 반영.
- 시장지표 선택 드롭다운(multiselect)의 옵션 목록도 `_load_symbols()` 캐시 클리어로 함께 갱신.

---

## 8. 파일별 구현 상세

### 8.1. `dashboard/app.py` (전면 변경 — 라우터)

```python
"""FinSight — st.navigation() entry point."""
import sys
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="FinSight", page_icon="🏠", layout="wide")

# sys.path bootstrap
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
DASH = ROOT / "dashboard"
for _p in (str(ROOT), str(DASH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

pg = st.navigation({
    "분석": [
        st.Page("views/market_trend.py", title="시장지표트랜드", icon="🏠", default=True),
        st.Page("views/ma_analysis.py",  title="이동평균분석",   icon="📈"),
        st.Page("views/daily_market.py", title="시장지표일별시세", icon="📋"),
    ],
    "관리": [
        st.Page("views/admin_symbols.py", title="Admin Symbols", icon="🗂️"),
    ],
})

pg.run()
```

### 8.2. `dashboard/views/market_trend.py` (이동)

- 기존 `app.py`의 차트 로직 **전체**를 이동.
- `st.set_page_config()` 호출 제거 (app.py에서 처리).
- sys.path 부트스트랩 코드 제거 (app.py에서 처리).
- 보유현황 Refresh 버튼 추가 (7장 참조).
- 그 외 로직은 **변경 없음**.

### 8.3. `dashboard/views/ma_analysis.py` (신규)

- 5장 설계 기반으로 신규 구현.
- 사이드바: 단일 지표 selectbox + 기간 프리셋 + MA 3개 selectbox.
- 메인: Plotly 차트 (원본 + MA선 중첩, 최고/최저/최근 표시, 분기 X축).
- CSV 다운로드 (원본 + MA값 포함).

### 8.4. `dashboard/views/daily_market.py` (전환)

- 기존 `pages/2_admin_prices.py` 기반.
- `require_admin()` 호출 제거.
- `st.set_page_config()` 호출 제거.
- sys.path 부트스트랩 코드 제거.
- 기간 프리셋 조회 조건 추가 (`periods.py` 재사용).
- `list_daily_prices()` 서비스 함수로 기간 범위 조회.

### 8.5. `dashboard/views/admin_symbols.py` (이동)

- 기존 `pages/1_admin_symbols.py`를 그대로 이동.
- `st.set_page_config()` 호출 제거.
- sys.path 부트스트랩 코드 제거.
- `require_admin()` 유지.
- 기능 변경 없음.

### 8.6. `dashboard/finsight_lib/ma_config.py` (신규)

- MA 옵션 상수 (`MA_OPTIONS`, `MA_DEFAULTS`).
- MA 라인 스타일 상수 (`MA_LINE_STYLES`).

### 8.7. `dashboard/finsight_lib/transform.py` (확장)

- `calc_sma()` 함수 추가 (5.4절 참조).

### 8.8. `dashboard/finsight_lib/palette.py` (확장)

- `MA_LINE_STYLES` 를 `ma_config.py` 에 분리하므로, palette.py 변경 최소화.
- 필요 시 MA 전용 색상 상수 추가.

### 8.9. `dashboard/services/price_service.py` (확장)

- `list_daily_prices()` 추가 (6.3절 참조).
- 기존 함수 (`get_series`, `list_symbol_coverage`, `count_prices`, `list_prices`) 유지.

---

## 9. 파일 작성 시 주의사항

### 인코딩 (Windows 환경)

이전 [PLAN-front-20260622](./PLAN-front-20260622.md) 14장과 동일:

1. **Shell 도구** + `[System.IO.File]::WriteAllText(..., [Encoding]::UTF8)` 로 파일 작성.
2. Python 소스 내 한글 문자열은 **유니코드 이스케이프** 로 작성:
   - `"\uc2dc\uc7a5\uc9c0\ud45c\ud2b8\ub80c\ub4dc"` (시장지표트랜드)
   - `"\uc774\ub3d9\ud3c9\uade0\ubd84\uc11d"` (이동평균분석)

### `st.navigation()` 전환 관련

- `st.set_page_config()` 는 `app.py` 에서만 **1회** 호출. 뷰 파일에서 호출하면 `StreamlitAPIException` 발생.
- 각 뷰 파일의 sys.path 부트스트랩 코드 **제거** (app.py 에서 처리).
- `st.Page()` 의 경로는 `app.py` 기준 **상대 경로** (`"views/xxx.py"`).

### 파일 작성 검증

각 단계 완료 후 다음으로 기동 검증:
```bash
uv run streamlit run dashboard/app.py
```

---

## 10. 단계별 실행 계획

### 단계 0. 사전 준비

- [ ] `dashboard/views/` 디렉토리 및 `__init__.py` 생성
- [ ] `dashboard/finsight_lib/ma_config.py` 작성 — `MA_OPTIONS`, `MA_DEFAULTS`, `MA_LINE_STYLES`
- [ ] `dashboard/finsight_lib/transform.py` 에 `calc_sma()` 추가

### 단계 1. app.py 라우터 전환 + market_trend 분리

- [ ] 기존 `dashboard/app.py` 차트 로직을 `dashboard/views/market_trend.py` 로 이동
  - `st.set_page_config()` 제거
  - sys.path 부트스트랩 제거
  - 보유현황 Refresh 🔄 버튼 추가
- [ ] `dashboard/app.py` 를 `st.navigation()` 라우터로 전면 재작성
- [ ] 기동 확인: 시장지표트랜드 페이지가 기존과 동일하게 동작하는지 검증

### 단계 2. Admin Symbols 이동

- [ ] `dashboard/pages/1_admin_symbols.py` → `dashboard/views/admin_symbols.py` 이동
  - `st.set_page_config()` 제거
  - sys.path 부트스트랩 제거
  - `require_admin()` 유지
- [ ] 기동 확인: Admin Symbols 메뉴 진입 및 인증·CRUD 동작 확인

### 단계 3. 시장지표일별시세 구현

- [ ] `dashboard/services/price_service.py` — `list_daily_prices()` 추가
- [ ] `dashboard/views/daily_market.py` 작성
  - 기존 `2_admin_prices.py` 기반
  - `require_admin()` 제거 (일반 화면)
  - 기간 프리셋 조회 조건 추가
  - `list_daily_prices()` 사용
- [ ] 기동 확인: 시장지표일별시세 메뉴에서 단일 지표 + 기간 범위 조회·페이징 동작 확인

### 단계 4. 이동평균분석 구현

- [ ] `dashboard/views/ma_analysis.py` 작성
  - 사이드바: 단일 지표 selectbox + 기간 프리셋 + MA 3개 selectbox
  - 데이터 조회: `get_series()` 활용 (버퍼 기간 포함)
  - SMA 계산: `calc_sma()` 활용
  - 차트: Plotly (원본 + MA선, 최고/최저/최근, 분기 X축, 수직선)
  - CSV 다운로드 (원본 + MA값)
- [ ] 기동 확인: 이동평균분석 전체 기능 동작 확인

### 단계 5. 정리 및 최종 검증

- [ ] `dashboard/pages/1_admin_symbols.py` 삭제
- [ ] `dashboard/pages/2_admin_prices.py` 삭제
- [ ] `dashboard/pages/` 디렉토리 삭제 (빈 디렉토리)
- [ ] 전체 메뉴 순서 확인: 시장지표트랜드 → 이동평균분석 → 시장지표일별시세 → Admin Symbols
- [ ] 각 페이지 기능 통합 테스트
- [ ] import 경로 정리 및 미사용 import 제거

---

## 11. 완료 기준 (Definition of Done)

- [ ] 좌측 패널 메뉴가 **시장지표트랜드 | 이동평균분석 | 시장지표일별시세 | Admin Symbols** 순서로 표시된다.
- [ ] 시장지표트랜드는 기존과 동일하게 동작한다 (다중 선택, 정규화, 차트, CSV).
- [ ] 이동평균분석에서 단일 지표 + 기간 + MA 3개선을 설정하면 SMA 중첩 차트가 표시된다.
- [ ] 차트에 최고점·최저점·최근 값이 표시되고, 최근 일자에 수직선이 표시된다.
- [ ] X축에 분기 간격 눈금(`YYYY-NQ`)이 표시된다.
- [ ] 시장지표일별시세에서 단일 지표 + 기간 범위로 일별 시세를 조회할 수 있다 (인증 불요).
- [ ] Admin Symbols는 관리자 인증 후 기존과 동일하게 CRUD 동작한다.
- [ ] 보유현황 🔄 Refresh 버튼 클릭 시 보유현황 및 지표 드롭다운이 갱신된다.
- [ ] `uv run streamlit run dashboard/app.py` 로 로컬 기동 시 오류 없이 동작한다.

---

## 12. 리스크 및 고려사항

| 항목 | 내용 | 대응 |
| --- | --- | --- |
| `st.navigation()` 호환성 | Streamlit 1.36+ 필요 (현재 `>=1.58.0` — 충족) | requirements.txt 버전 확인 |
| `pages/` 디렉토리 잔존 | `st.navigation()` 사용 시에도 `pages/` 가 남아있으면 경고 발생 가능 | 단계 5에서 완전 삭제 |
| 대량 MA 데이터 조회 | MA3Y(750일) 버퍼 시 ~4.5년치 데이터 조회 필요 | `get_series()` 캐시(`ttl=3600`) 활용, 단일 지표이므로 데이터량 제한적 |
| MA 윈도우 부족 | 데이터 보유 기간이 MA 윈도우보다 짧은 경우 | 해당 MA선은 NaN → 차트에 표시되지 않음. 사용자에게 `st.warning` 안내 |
| `reference/fx_trend` 부재 | `.gitignore` 대상으로 저장소에 없음 | PRD 텍스트 스펙 기반으로 구현. 필요 시 로컬 참조 파일 별도 확인 |
| 분기 X축 포맷 | Plotly d3-time-format에 `%q`(분기) 미지원 | `tickmode="array"` + `tickvals`/`ticktext` 수동 생성 |
| 뷰 파일 인코딩 | Windows 환경 한글 리터럴 인코딩 문제 | Shell + UTF-8 명시 방식 또는 유니코드 이스케이프 사용 |
| 기존 페이지 import 경로 | `from dashboard.services.xxx` vs `from services.xxx` | app.py에서 DASH를 sys.path에 추가하므로 `from services.xxx` 통일 |

---

## 13. 의존성 변경

현재 `requirements.txt` 에 추가 패키지 불필요. Pandas `rolling()` 으로 SMA 계산 가능.

```
streamlit>=1.58.0    # st.navigation() 지원 (1.36+)
plotly>=6.8.0
sqlalchemy>=2.0
psycopg[binary]>=3.2
pandas>=2.2
numpy>=1.26
python-dotenv>=1.0
```

변경 없음.
