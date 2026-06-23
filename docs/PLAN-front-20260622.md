# FinSight 대시보드(시각화) 실행 계획 (PLAN-front-20260622)

> 본 문서는 [PRD-front-20260619](./PRD-front-20260619.md) **8장 Dashboard / 9장 기타 요구사항**을 구현하기 위한 계획이다.
> 관리자 화면(1차 완료, [PLAN-front-20260619](./PLAN-front-20260619.md))의 데이터 접근 계층·인증·연결을 재사용하고,
> Neon DB(`symbol_master`, `daily_price`)를 읽어 **Plotly 인터랙티브 차트**로 시각화한다.
> UI/UX 기준은 `reference/market_indicators/` 디렉토리(HTML 독립 대시보드 소스)를 따른다.

---

## 1. 목표

- 수집된 금융지표를 **다중 비교 차트**로 시각화하는 대시보드를 `dashboard/app.py` 에 구현한다.
- 좌측 패널에서 종목 선택·기간·정규화를 제어하고, 우측에 Plotly 차트와 CSV 다운로드를 제공한다.
- 기존 관리자 화면 진입점을 **좌측 패널 하단**에 배치한다.
- `app` 페이지 아이콘을 **홈 이모지(🏠)** 로 변경한다.
- 프런트 전용 **경량 `requirements.txt`** 를 분리한다.

---

## 2. 범위

### 2.1. 포함 (In Scope)

| 영역 | 기능 (PRD 8/9) |
| --- | --- |
| 종목 선택 패널 | `symbol_master` 테이블형 목록, 최대 10개 복수 선택, 선택 순서 기반 RAINBOW 색상 자동 배정, 선택 카운터 표시, [전체][해제][기본값] 버튼 |
| 기간 선택 | 종료일 default=오늘, 프리셋 `[1주|1개월|3개월|6개월|1년(default)|3년|10년|직접지정]` |
| 표시 방식 | **정규화(기준 100)** 또는 **원본 종가** 토글, 원본 선택 시 단위 차이 경고 |
| 차트 | Plotly 인터랙티브(range slider·모드바), 블룸버그 스타일 Dark/Light 테마 토글 |
| 데이터 내보내기 | 차트 데이터 CSV 다운로드 (utf-8-sig) |
| 관리자 진입점 | 좌측 패널 하단에 종목마스터/종가내역 관리 링크 배치 |
| 배포 | 프런트 전용 경량 `requirements.txt` |

### 2.2. 제외 (Out of Scope)

- 신규 지표 산출·기술 분석(이동평균 등) — 후속.
- 관리자 화면 기능 변경(이미 완료분 재사용).

---

## 3. Reference 디자인 해석 (`reference/market_indicators/`)

`reference/market_indicators/src/generate.py` 는 독립 실행 HTML 대시보드이며 Streamlit 구현의 **UI/UX 기준**이다.

### 3.1. 좌측 패널 구조

```
┌──────────────────────────────────────────────┐
│ 시장지표 선택  [4/10]  [전체][해제][기본값]     │
├──┬──┬──────────┬──────────┬──────┬──────┬────┤
│✓ │색│ SYMBOL   │ 지수명   │ FROM │  TO  │ 건수│
├──┼──┼──────────┼──────────┼──────┼──────┼────┤
│☑ │🔴│ KS11     │ KOSPI 지수│ ...  │ ...  │ N  │  ← 선택됨, 빨강 배정
│☑ │🟠│ KQ11     │ KOSDAQ 지수│ ...  │ ...  │ N  │  ← 선택됨, 주황 배정 → 드롭다운 변경 가능
│☐ │  │ KS200    │ KOSPI 200 │ ...  │ ...  │ N  │  ← 미선택
│  │ ...                                        │
├──┴──┴──────────┴──────────┴──────┴──────┴────┤
│  🗂️ 종목마스터 관리  /  📊 종가내역 조회        │  ← 관리자 진입점
└──────────────────────────────────────────────┘
```

- **체크박스 셀**: 선택 여부 토글.
- **색상 셀**: 선택된 종목은 RAINBOW 15색 중 하나를 드롭다운으로 선택. 미선택 종목은 빈칸. **기본값은 선택 순서에 따라 자동 배정**하고, 사용자가 언제든 변경할 수 있다.
- **선택 카운터** `N/10`: 선택 수 / 최대값. 최대 초과 시 경고.
- **색상 초기 배정**: 처음 선택 시 `session_state["color_map"]`에 없으면 순서 기반으로 RAINBOW 색상 자동 배정. 이후 사용자가 드롭다운으로 변경하면 `color_map[symbol_id]` 에 저장(재선택해도 유지).

### 3.2. RAINBOW 색상 팔레트 (15색)

사용자가 선택할 수 있는 색상 목록. `data_editor` 의 `SelectboxColumn` 옵션으로 제공한다.

```python
# reference/market_indicators/ 색상 + 무지개 7색 통합 15종
RAINBOW: list[str] = [
    "#e74c3c",  # 빨강
    "#e67e22",  # 주황
    "#f1c40f",  # 노랑
    "#2ecc71",  # 초록
    "#3498db",  # 파랑
    "#4834d4",  # 남색
    "#9b59b6",  # 보라
    "#4e9af1",  # 하늘
    "#f1a34e",  # 살구
    "#6af178",  # 연두
    "#1abc9c",  # 청록
    "#f39c12",  # 황금
    "#a78bfa",  # 라벤더
    "#f14e4e",  # 진홍
    "#95a5a6",  # 회색
]
```

**색상 상태 관리 (`session_state["color_map"]`)**:

```python
color_map: dict[int, str]  # {symbol_id: hex_color}
```

- 종목이 **처음 선택될 때**: 이미 `color_map` 에 있으면 유지, 없으면 기존 선택 색상과 겹치지 않는 RAINBOW 첫 색상 자동 배정.
- 사용자가 **드롭다운으로 색상 변경**: `color_map[symbol_id]` 업데이트.
- 종목을 **해제 후 재선택**: `color_map` 에 이전 색상이 남아있으므로 그대로 복원.

### 3.3. 차트 테마

블룸버그 단말 스타일을 참조하여 두 가지 테마를 정의한다.

| 속성 | Dark | Light |
| --- | --- | --- |
| paper/plot_bgcolor | `#0d1117` / `#0d1117` | `#ffffff` / `#f8f9fa` |
| font_color | `#e6edf3` | `#1f1f1f` |
| grid_color | `#2a2a2a` | `#e0e0e0` |
| line_color | `#30363d` | `#cccccc` |
| slider_bg | `#161b22` | `#e8e8e8` |
| legend_bg | `rgba(13,17,23,0.85)` | `rgba(255,255,255,0.9)` |
| hover_bg | `#161b22` | `#ffffff` |
| hover_font | `#e6edf3` | `#1f1f1f` |

### 3.4. 정규화 방식

```
정규화값 = (종가 / 구간 내 첫 유효 종가) × 100
```

- y축 라벨: 정규화 → `"정규화 지수 (기준 100)"`, 원본 → `"종가/지표"`.
- 구간 내 첫 유효값이 없는 종목은 NaN 유지 → 차트에서 gap 처리.

### 3.5. 단선 보정 (ffill)

종목별 거래일 불일치로 발생하는 NaN을 **전일 값 forward-fill** 로 보정한다.

---

## 4. 디렉토리 구조 (추가/변경분)

```
FinSight/
├── dashboard/
│   ├── app.py                      # [변경] 대시보드 메인으로 전면 재작성
│   ├── lib/                        # [신규] 시각화 유틸 패키지
│   │   ├── __init__.py
│   │   ├── palette.py              # RAINBOW, CHART_THEMES
│   │   ├── periods.py              # 기간 프리셋 → from_date 계산
│   │   └── transform.py            # trade_dt→datetime, 정규화, wide 피벗, ffill
│   ├── pages/
│   │   ├── 1_admin_symbols.py      # (완료, 변경 없음)
│   │   └── 2_admin_prices.py       # (완료, 변경 없음)
│   └── services/
│       ├── price_service.py        # [확장] get_series(), list_symbol_coverage() 추가
│       └── (기존 connection/auth/symbol_service — 변경 없음)
├── .streamlit/
│   └── config.toml                 # [신규] base = "dark"
└── requirements.txt                # [변경] 프런트 전용 경량
```

---

## 5. sys.path 부트스트랩 전략

`dashboard/app.py` 는 Streamlit의 엔트리포인트로 실행된다. `from lib.palette import ...` 형태의 상대 임포트를 쓰려면 `dashboard/` 디렉토리를 sys.path에 추가해야 한다.

```python
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
DASH = ROOT / "dashboard"
for _p in (str(ROOT), str(DASH)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

- `ROOT` 추가: `from src.db.models import ...` 등 백엔드 모듈 접근
- `DASH` 추가: `from lib.palette import ...`, `from services.connection import ...` 접근

---

## 6. 데이터 접근 계층 (`dashboard/services/price_service.py` 확장)

기존 관리자 함수(`count_prices`, `list_prices`)를 유지하고 대시보드용 2개 추가.

| 함수 | 설명 | 캐시 |
| --- | --- | --- |
| `get_series(symbol_ids: tuple, from_dt: str, to_dt: str)` | 다종목 기간 종가 조회. `trade_dt BETWEEN` 활용. 반환: `[{symbol_id, trade_dt, close_price}]` | `@st.cache_data(ttl=3600)` |
| `list_symbol_coverage()` | 종목별 `MIN/MAX/COUNT(daily_price)` + `symbol_master` 조인. 반환: `[{symbol_id, symbol_nm, from_dt, to_dt, cnt}]` | `@st.cache_data(ttl=3600)` |
| `symbol_service.list_symbols()` 래퍼 | 앱 모듈 레벨에서 `@st.cache_data(ttl=86400)` 로 캐싱 | `ttl=86400` |

- `symbol_ids` 는 캐시 키 일관성을 위해 **정렬된 tuple** 로 전달: `tuple(sorted(ids))`.
- `trade_dt` 는 VARCHAR(8) YYYYMMDD → 사전식 비교이므로 `BETWEEN` 범위 조회 정확.

---

## 7. 유틸 계층 (`dashboard/lib/`)

### 7.1. `palette.py`

```python
RAINBOW: list[str]                       # 15색 (선택 순서 → 색상)
CHART_THEMES: dict[str, dict[str, str]]  # "Dark" / "Light" 테마 딕셔너리
```

파일 작성 시 한글 리터럴을 피하고 **유니코드 이스케이프** 또는 영문 키로 작성한다
(Windows 환경에서 Write 도구의 인코딩 문제 방지).

### 7.2. `periods.py`

```python
PRESETS: list[str]         # ["1주", "1개월", ..., "직접지정"]
DEFAULT_PRESET = "1년"
def from_date_by_preset(to_date: date, preset: str) -> date: ...
```

- `dateutil` 미사용. `calendar.monthrange` + `date.replace()` 기반.
- 파일 작성 시 한글 문자열은 유니코드 이스케이프(`\uXXXX`)로 저장.

### 7.3. `transform.py`

```python
def to_wide(rows: list[dict], symbol_id_to_nm: dict[int, str]) -> pd.DataFrame:
    """
    1. trade_dt (YYYYMMDD) → pd.to_datetime(format="%Y%m%d") 로 인덱스 변환
    2. long → wide pivot (symbol_nm 컬럼)
    3. ffill() 로 거래일 불일치 단선 보정
    """

def normalize_100(wide: pd.DataFrame) -> pd.DataFrame:
    """구간 내 첫 유효값을 100으로 정규화"""
```

---

## 8. 화면 설계 (`dashboard/app.py`)

### 8.1. 전체 레이아웃

```
┌────────────────── st.sidebar ──────────────────────────┐
│ ### 시장지표 선택   [N/10]                               │
│ [전체]  [해제]  [기본값]                                  │
│ ─────────────────────────────────────────────────────── │
│ st.data_editor                                          │
│  ✓  색상  SYMBOL  자산명  FROM   TO    건수              │
│ ──────────────────────────────────────────────────────  │
│ ─────────────────────────────────────────────────────── │
│ #### 기간 설정                                           │
│ 종료일: [오늘]    프리셋: [1년 ▼]                         │
│ ─────────────────────────────────────────────────────── │
│ #### 표시 방식                                           │
│ 🔘 정규화 (기준 100)  /  ○ 원본 종가                     │
│ ─────────────────────────────────────────────────────── │
│ 🗂️ 종목마스터 관리   📊 종가내역 조회   ← 관리자 진입점    │
└────────────────────────────────────────────────────────┘

┌──────────── 메인 영역 ─────────────────────────────────┐
│ ### 📈 FinSight 대시보드   [차트 배경: ◉ Dark  ○ Light]  │
│                                                         │
│ ┌──────────────────────────────────────────────────┐    │
│ │  Plotly 차트 (height=580)                         │    │
│ │  · 종목별 line trace (color_map[symbol_id] 사용)   │    │
│ │  · hovermode="x unified"                          │    │
│ │  · 하단 range slider                              │    │
│ └──────────────────────────────────────────────────┘    │
│                                                         │
│ [📥 CSV 다운로드]                                        │
└────────────────────────────────────────────────────────┘
```

### 8.2. 좌측 패널 세부 — 종목 선택 (`st.data_editor`)

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `✓` (선택) | CheckboxColumn | 선택 여부 |
| `색상` | SelectboxColumn | RAINBOW 15색 중 선택. 선택된 종목만 편집 가능(미선택은 빈칸) |
| `SYMBOL` | TextColumn (disabled) | 종목 코드 |
| `자산명` | TextColumn (disabled) | 종목 한글명 |
| `FROM` | TextColumn (disabled) | 최초 데이터 일자 |
| `TO` | TextColumn (disabled) | 최근 데이터 일자 |
| `건수` | NumberColumn (disabled) | 보유 데이터 수 |
| `_id` | — (hidden) | symbol_id |

> `SelectboxColumn` 의 `options` 는 `RAINBOW` hex 리스트. 사용자는 드롭다운에서 색상 hex 문자열을 직접 선택한다.
> 색상 hex가 직관적이지 않으므로 향후 색상명 매핑 추가를 고려할 수 있으나, 1차는 hex 문자열로 진행한다.

**색상 초기화 로직 (`_ensure_colors`):**

```python
def _ensure_colors(sel_order: list[int], color_map: dict[int, str]) -> None:
    """선택된 종목 중 color_map에 없는 종목에만 RAINBOW 자동 배정 (중복 피함)."""
    used = set(color_map.get(s) for s in sel_order if s in color_map)
    for sid in sel_order:
        if sid not in color_map:
            for c in RAINBOW:
                if c not in used:
                    color_map[sid] = c
                    used.add(c)
                    break
            else:
                color_map[sid] = RAINBOW[0]  # 15색 모두 소진된 경우 (비정상)
```

**DataFrame 구성 시 색상 컬럼 처리:**

```python
for s in all_syms:
    sid = s["symbol_id"]
    is_sel = sid in sel_set
    rows.append({
        "선택": is_sel,
        # 선택된 종목은 현재 배정 색상, 미선택은 빈 문자열(SelectboxColumn은 None 미지원)
        "색상": color_map.get(sid, RAINBOW[0]) if is_sel else "",
        "SYMBOL": s["symbol"],
        ...
    })
```

**편집 결과 처리 — 색상 변경 반영:**

```python
for _, row in edited.loc[edited["선택"]].iterrows():
    sid = int(row["_id"])
    if row["색상"] in RAINBOW:
        color_map[sid] = row["색상"]   # 사용자가 변경한 색상 저장
    elif sid not in color_map:
        pass  # _ensure_colors가 다음 rerun에서 자동 배정
```

**버튼 → data_editor 상태 재초기화 방식:**

```python
# 버튼 클릭 시 editor_ver 증가 → key 변경 → data_editor 재초기화
if btn.button("전체"):
    st.session_state["selected_order"] = all_ids[:_MAX_SELECT]
    st.session_state["editor_ver"] += 1
```

**최대 10개 초과 처리:**

```python
if len(new_order) > _MAX_SELECT:
    new_order = new_order[:_MAX_SELECT]
    st.toast("최대 10개까지 선택 가능합니다.", icon="⚠️")
```

**편집 결과 처리 (선택 순서 보존):**

```python
# 기존 순서 유지 + 새로 추가된 것만 뒤에 append
kept  = [sid for sid in prev_order if sid in new_sel_set]
added = [sid for sid in new_sel_set if sid not in set(prev_order)]
new_order = kept + added
```

### 8.3. 기간 설정

```python
to_date  = st.date_input("종료일", value=date.today())
preset   = st.selectbox("기간 프리셋", options=PRESETS, index=PRESETS.index("1년"))
if preset == "직접지정":
    from_date = st.date_input("시작일", ...)
else:
    from_date = from_date_by_preset(to_date, preset)
    st.caption(f"시작일: {from_date}")
```

### 8.4. 차트 배경 토글

참고 이미지와 동일하게 **라디오 버튼(가로)** 으로 구현:

```python
theme_choice = st.radio("차트 배경", ["Dark", "Light"], horizontal=True)
```

차트 렌더링 시 `CHART_THEMES[theme_choice]` 딕셔너리로 `paper_bgcolor`, `plot_bgcolor`, `font_color` 등을 `fig.update_layout()` 에 적용한다. Plotly `template` 대신 **직접 색상 지정 방식**으로 블룸버그 스타일을 구현한다.

### 8.5. 관리자 진입점 (좌측 패널 하단)

```python
# 사이드바 하단
st.divider()
st.page_link("pages/1_admin_symbols.py", label="🗂️ 종목마스터 관리")
st.page_link("pages/2_admin_prices.py",  label="📊 종가내역 조회")
```

### 8.6. `app` 홈 아이콘

```python
st.set_page_config(page_title="FinSight", page_icon="🏠", layout="wide")
```

Streamlit 파일 기반 멀티페이지에서 `app.py` 의 사이드바 nav 라벨은 기본 "app" 으로 표시된다.
`page_icon="🏠"` 으로 아이콘을 홈 이모지로 변경한다.

---

## 9. 경량 requirements.txt (PRD 9장)

백엔드 수집 패키지(`finance-datareader`, `yfinance` 등)를 제외한 프런트 전용 최소 구성:

```
streamlit>=1.58.0
plotly>=6.8.0
sqlalchemy>=2.0
psycopg[binary]>=3.2
pandas>=2.2
numpy>=1.26
python-dotenv>=1.0
```

- 백엔드/CI 는 `uv.lock` 기반 `uv sync --frozen` 사용 → `requirements.txt` 변경에 영향 없음.
- 파일 작성 시 `[System.IO.File]::WriteAllText(..., UTF8)` 방식으로 인코딩 문제를 방지한다.

---

## 10. 파일별 구현 시 주의사항

### 한글 리터럴 인코딩 문제

Windows 환경에서 Write 도구로 한글 문자열이 포함된 Python 파일을 저장하면 인코딩이 깨져 `ImportError` 가 발생한다. 이를 방지하기 위해:

1. **Shell 도구** + `[System.IO.File]::WriteAllText(..., [Encoding]::UTF8)` 로 파일 작성.
2. Python 소스 내 한글 문자열은 **유니코드 이스케이프** 로 작성:
   - `"1\ub144"` (1년), `"1\uac1c\uc6d4"` (1개월), `"\uc9c1\uc811\uc9c0\uc815"` (직접지정)
3. 영문 키(색상명 등)는 ASCII 범위에서 작성.

### 파일 작성 검증

파일 작성 후 반드시 다음으로 임포트 검증:
```bash
uv run python -c "from lib.palette import RAINBOW, CHART_THEMES; print('OK')"
```
검증은 `dashboard/` 디렉토리를 working directory로 실행한다.

---

## 11. 단계별 실행 계획

### 단계 0. 사전 준비 (파일 작성 환경)
- [x] `dashboard/finsight_lib/__init__.py` 생성 (`lib` → `finsight_lib` 로 변경, 네임스페이스 충돌 방지)
- [x] `dashboard/finsight_lib/palette.py` 작성 — `RAINBOW`(15색), `COLOR_MAP`(영문명→hex), `RAINBOW_NAMES`(영문명 목록), `COLOR_EMOJI`, `CHART_THEMES`
- [x] `dashboard/finsight_lib/periods.py` 작성 — `PRESETS`, `from_date_by_preset()` (calendar 기반, dateutil 미사용)
- [x] `dashboard/finsight_lib/transform.py` 작성 — `to_wide()` (ffill 포함), `normalize_100()`
- [x] `.streamlit/config.toml` 작성 (`base = "dark"`, BOM-free UTF-8)
- [x] `requirements.txt` 프런트 전용 경량화 (백엔드 수집 패키지 제외)

> **실행 환경 주의**: Write 도구의 BOM 인코딩 문제로 파일 작성은 Python `pathlib.Path.write_text(encoding="utf-8")` 방식을 사용했다. 향후 lib 파일 수정 시에도 동일 방식 적용.

### 단계 1. 데이터 서비스 확장 (`price_service.py`)
- [x] `get_series(symbol_ids: tuple, from_dt: str, to_dt: str)` 추가 (`@st.cache_data(ttl=3600)`)
- [x] `list_symbol_coverage()` 추가 (`@st.cache_data(ttl=3600)`)
- [x] 기존 `count_prices`, `list_prices` 유지 (관리자 페이지 호환), `PAGE_SIZE=30`

### 단계 2. `dashboard/app.py` 구현
- [x] sys.path 부트스트랩 (ROOT + DASH 모두 추가)
- [x] `page_icon="🏠"` 설정
- [x] session_state 초기화 (`selected_order`, `editor_ver`, `chart_theme`, `color_map`)
- [x] 사이드바: 선택 패널 (data_editor — ●이모지·✓체크박스·색상드롭다운·SYMBOL·자산명·FROM·TO·건수)
- [x] 사이드바: [전체][해제][기본값] 버튼 + 선택 카운터, 최대 10개 초과 토스트
- [x] 사이드바: 기간 설정 (종료일 date_input + 프리셋 selectbox + 직접지정)
- [x] 사이드바: 정규화 토글 (원본 선택 시 경고 표시)
- [x] 사이드바: 관리자 진입점 링크 (하단 `st.page_link`)
- [x] 메인: 제목 + 차트 배경 라디오 토글 (Dark/Light, horizontal)
- [x] 메인: Plotly 차트 (CHART_THEMES 직접 적용, range slider, hovermode x unified)
- [x] 메인: CSV 다운로드 버튼 (utf-8-sig)
- [x] 색상 SelectboxColumn — hex 대신 **영문명** (`Red`, `Orange` 등) + 컬러 이모지 `●` 컬럼 추가 (2026-06-22 보완)

### 단계 3. 검증
- [x] 로컬 `uv run streamlit run dashboard/app.py` 기동 확인 (2026-06-22)
- [ ] 종목 선택 / 해제 / 기본값 버튼 동작 및 색상 배정 확인
- [ ] 기간 프리셋 전체 선택지 동작 확인
- [ ] 정규화 ↔ 원본 전환 확인
- [ ] Dark ↔ Light 테마 전환 확인
- [ ] CSV 다운로드 파일 내용 확인
- [ ] 관리자 진입점 링크 클릭 확인
- [ ] 10개 초과 선택 시 토스트 경고 확인
- [ ] Streamlit Community Cloud 재배포 확인

---

## 12. 완료 기준 (Definition of Done)

- `dashboard/app.py` 가 대시보드 화면으로 동작한다.
- 최대 10개 종목을 선택할 수 있고, 선택 순서에 따라 RAINBOW 색상이 자동 배정된다.
- 기간 프리셋 7종 + 직접 지정이 정확하게 동작한다.
- 정규화(기준 100) / 원본 종가 전환이 정확하게 동작한다.
- 차트가 블룸버그 스타일 Dark 테마로 기본 표시되며 Light 전환이 가능하다.
- 차트 데이터의 CSV 다운로드가 동작한다.
- 관리자 화면 진입점이 좌측 패널 하단에 위치한다.
- 프런트 전용 경량 `requirements.txt` 로 Streamlit Community Cloud 배포가 가능하다.

---

## 13. 변경 이력 (2026-06-23)

### 좌측 패널 선택 방식 재설계

PRD 8장 "좌측 패널 스타일은 reference 참조, 수집된 목록 리스트에서 색상을 지정하여 선택" 요건을 구글 그래프 옵션 스타일로 재해석하여 구현을 변경했다.

#### 변경 전/후 패널 구조

**변경 전 (`st.data_editor` 기반 체크박스 표)**
```
┌──┬──┬──────────┬──────────┬──────┬──────┬────┐
│✓ │색│ SYMBOL   │ 지수명   │ FROM │  TO  │ 건수│
├──┼──┼──────────┼──────────┼──────┼──────┼────┤
│☑ │🔴│ KS11     │ KOSPI 지수│ ...  │ ...  │ N  │
│☑ │🟠│ KQ11     │ KOSDAQ   │ ...  │ ...  │ N  │
│☐ │  │ KS200    │ KOSPI 200│ ...  │ ...  │ N  │
└──┴──┴──────────┴──────────┴──────┴──────┴────┘
```

**변경 후 (`st.multiselect` + 별도 색상 지정 + 참고 테이블)**
```
┌──────────────────────────────────────────────┐
│ 시장지표 선택   [4/10]                        │
│ [전체]  [해제]  [기본값]                       │
│ ┌────────────────────────────────────────┐    │
│ │ 지표를 선택하세요 (최대 10개)  ▼       │    │  <- st.multiselect
│ └────────────────────────────────────────┘    │
│                                               │
│ 지표별 색상 지정                               │
│ 🔴 KS11  KOSPI 지수   [Red        ▼]         │
│ 🟠 KQ11  KOSDAQ 지수  [Orange     ▼]         │  <- st.selectbox (지표별)
├────────────────────────────────────────────── │
│ 기간 설정 / 표시 방식                          │
├────────────────────────────────────────────── │
│ 지표 데이터 보유현황  (참고용 읽기 전용)         │
│ Symbol  지표명(굵게)  From        To   건수   │  <- HTML 커스텀 테이블
│ KS11    KOSPI 지수   1990-01-02  ...  7,258  │
│ KQ11    KOSDAQ 지수  2000-10-16  ...  6,318  │
└──────────────────────────────────────────────┘
```

#### 항목별 변경 내용

| 항목 | 변경 전 | 변경 후 |
| --- | --- | --- |
| 선택 방식 | `st.data_editor` 체크박스 표 | `st.multiselect` 드롭다운 (구글 스타일) |
| 색상 지정 | 표 내 `SelectboxColumn` | 선택 지표별 `st.selectbox` 행 (이모지 + 지표명 + 색상 드롭다운) |
| 참고 목록 | 선택 UI와 혼합 (같은 표) | 별도 HTML 커스텀 테이블로 분리 (읽기 전용) |
| 지표명 서체 | 보통 굵기 | **굵게** (`font-weight: 700`) |
| FROM/TO 포맷 | `YYYYMMDD` | `yyyy-mm-dd` |
| 건수 포맷 | 숫자 그대로 | 천단위 콤마 (예: `7,258`) |
| 테이블 폰트 | Streamlit 기본 | `0.71rem` (축소), 여백 최소화 |
| 상태 관리 | `editor_ver` + `color_map` dict | `ms_symbols` key + `cs_{sid}` key per symbol |
| 관련 파일 | `app.py` | `app.py` 전면 재작성 (2026-06-23) |

---

## 14. 리스크 및 고려사항

| 항목 | 내용 | 대응 |
| --- | --- | --- |
| 파일 인코딩 오류 | Write 도구의 한글 리터럴 저장 시 인코딩 문제로 ImportError | Shell `[System.IO.File]::WriteAllText` + 유니코드 이스케이프로 작성 |
| 대량 조회 성능 | 10종목 × 10년 → 수만 행 | `symbol_id IN + trade_dt BETWEEN` 단일 쿼리 + `st.cache_data(ttl=3600)` |
| 거래일 불일치 단선 | 종목별 휴장일 차이 → 차트 단선 | `to_wide()` 내 `ffill()` 로 보정 |
| 정규화 기준 결측 | 구간 시작일에 데이터 없는 경우 | 구간 내 첫 유효값 사용, 없으면 해당 종목 NaN 유지(gap) |
| Cloud requirements 위치 | Streamlit Cloud 는 루트 `requirements.txt` 사용 | 루트를 프런트 경량으로 유지 (백엔드는 `uv.lock`) |
| data_editor 상태 재초기화 | 버튼 클릭 시 data_editor 내부 상태가 잔존 | `editor_ver` 카운터로 key 변경 → 강제 재초기화 |
| ~~색상 SelectboxColumn hex 가독성~~ | ~~드롭다운에 hex 문자열 표시~~ | **해결 완료** — 영문 색상명(`Red`, `Orange` 등)으로 변경 + `●` 컬러 이모지 컬럼 추가 (2026-06-22) |
| 원본 표시 y축 스케일 | 종목별 단위 극단적 차이 (KS200≈300 vs BTC≈100,000) | 단일 y축 유지 + "정규화를 권장합니다" 경고 표시 |
