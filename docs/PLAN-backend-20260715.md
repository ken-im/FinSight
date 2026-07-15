# FinSight FRED 수집 확장 실행 계획 (PLAN-backend-20260715)

> 본 문서는 [PRD-20260715](./PRD-20260715.md)를 구현하기 위한 실행 계획이다.
> 기존 수집 파이프라인([PLAN-backend-20260617](./PLAN-backend-20260617.md))의 구조를 유지하면서,
> **FRED 수집기 추가**, **종목마스터 컬럼 확장**, **FRED 10종목 시드 등록**을 반영한다.

---

## 1. 목표

- 미연방준비은행 **FRED 데이터 10종**을 기존 수집 파이프라인에 추가한다.
- 종목마스터에 **`data_frequency`** (데이터 주기) 및 **`category`** (분류) 컬럼을 추가한다.
- 기존 데이터(16종목 + daily_price)가 **유실되지 않도록** 안전하게 스키마를 변경한다.
- 기존 `src.collect` 배치의 **사용법을 그대로 유지**한다.

---

## 2. 범위

### 2.1. 포함 (In Scope)

| 영역 | 작업 |
| --- | --- |
| 스키마 변경 | `symbol_master`에 `data_frequency`, `category` 컬럼 추가 (ALTER TABLE) |
| 기존 데이터 보정 | 기존 16종목에 `data_frequency='Daily'`, `category` 값 설정 |
| ORM 모델 | `SymbolMaster` 클래스에 신규 컬럼 반영 |
| FRED 수집기 | `src/collectors/fred_collector.py` 신규 작성 |
| 수집 배치 연동 | `collect.py`의 `_COLLECTORS`에 `"FRED"` 매핑 추가 |
| 종목 시드 | `symbols_seed.py`에 FRED 10종목 추가 |
| 관련 서비스 | `symbol_service.py`, Admin 화면에 신규 컬럼 반영 |

### 2.2. 제외 (Out of Scope)

- PPI/CPI의 YoY% 변환 (대시보드 시각화 단계에서 처리)
- USREC 경기침체 구간 시각화 (별도 PRD)
- Alembic 마이그레이션 도입 (현재 `create_all` 방식 유지, 1회성 ALTER TABLE 스크립트로 처리)

---

## 3. 추가 수집 대상 FRED 종목

| source | symbol | symbol_nm | data_frequency | category | remark |
| --- | --- | --- | --- | --- | --- |
| FRED | FEDFUNDS | Fed 기준금리 | Monthly | FRED | Effective Federal Funds Rate |
| FRED | T10Y3M | 장단기금리차 | Daily | FRED | 10-Year Minus 3-Month Treasury |
| FRED | PPIACO | 생산자물가지수(PPI) | Monthly | FRED | Producer Price Index: All Commodities |
| FRED | CPIAUCSL | 소비자물가지수(CPI) | Monthly | FRED | Consumer Price Index for All Urban Consumers |
| FRED | DFII10 | 미국채10년물 | Daily | FRED | 10-Year Treasury Yield |
| FRED | DGS3MO | 미국채3개월물 | Daily | FRED | 3-Month Treasury Yield |
| FRED | UNRATE | 실업률 | Monthly | FRED | Unemployment Rate |
| FRED | NFCI | 금융상황지수 | Weekly | FRED | Chicago Fed National Financial Conditions Index |
| FRED | HOUST | 신규주택착공 | Monthly | FRED | New Privately-Owned Housing Units Started |
| FRED | USREC | 경기침체구간 | Monthly | FRED | NBER Recession Indicators (1=침체) |

---

## 4. 스키마 변경

### 4.1. 추가 컬럼

| 컬럼 | 타입 | nullable | 설명 |
| --- | --- | --- | --- |
| `data_frequency` | `VARCHAR(20)` | Yes | 데이터 주기: Daily, Weekly, Monthly, Yearly, Irregular |
| `category` | `VARCHAR(20)` | Yes | 분류: Market, Stock, FRED 등 (어드민 화면에서 수정 가능) |

- **nullable**: 기존 행에 영향을 주지 않기 위해 `NULL` 허용.
- Alembic 미사용 → 1회성 마이그레이션 스크립트(`src/migrate_v2.py`)로 처리.

### 4.2. 마이그레이션 스크립트 (`src/migrate_v2.py`)

```python
"""symbol_master 스키마 확장 (data_frequency, category 컬럼 추가)."""
# 1. ALTER TABLE ADD COLUMN IF NOT EXISTS
# 2. 기존 16종목에 data_frequency='Daily' 설정
# 3. 기존 종목에 category 기본값 설정 (FDR/YAHOO → Market 또는 Stock 분류)
```

실행 순서:
1. `ALTER TABLE symbol_master ADD COLUMN IF NOT EXISTS data_frequency VARCHAR(20);`
2. `ALTER TABLE symbol_master ADD COLUMN IF NOT EXISTS category VARCHAR(20);`
3. `UPDATE symbol_master SET data_frequency = 'Daily' WHERE data_frequency IS NULL;`
4. 기존 종목 category 일괄 설정 (아래 표 참조)

### 4.3. 기존 종목 category 분류

| symbol | 현재 source | category |
| --- | --- | --- |
| KS11, KQ11, KS200, DJI, IXIC, US500, VIX, ^N225, SSEC, HSI | FDR/YAHOO | Market |
| GC=F, CL, BTC/USD, ETH/USD | FDR/YAHOO | Market |
| AAPL, 005930 | FDR | Stock |

> PRD: "지표들에 대한 분류는 어드민 화면을 통하여 수정할 예정" — 초기 값만 설정하고 이후 관리자가 조정.

### 4.4. ORM 모델 변경 (`src/db/models.py`)

```python
class SymbolMaster(Base):
    # ... 기존 컬럼 ...
    data_frequency: Mapped[str | None] = mapped_column(
        String(20), comment="데이터 주기 (Daily, Weekly, Monthly, Yearly, Irregular)"
    )
    category: Mapped[str | None] = mapped_column(
        String(20), comment="분류 (Market, Stock, FRED)"
    )
```

---

## 5. FRED 수집기 (`src/collectors/fred_collector.py`)

### 5.1. 수집 방식

- FinanceDataReader의 FRED 지원 기능 활용: `fdr.DataReader('FRED:SYMBOL', start, end)`
- 종목마스터에 `source='FRED'`, `symbol='FEDFUNDS'`로 저장
- 수집기 내부에서 `f"FRED:{symbol}"` 형태로 조합하여 FDR 호출

### 5.2. 데이터 특성

| 항목 | 설명 |
| --- | --- |
| 반환 컬럼 | `Close` (또는 `Value`) 단일 값 |
| OHLCV | **없음** — `open_price`, `high_price`, `low_price`, `volume` 모두 `None` |
| 적재 컬럼 | `close_price`에 매핑, 나머지 nullable 컬럼은 `None` |
| 인터페이스 | `collect_daily_prices(symbol, start, end) → DataFrame` — 기존 수집기와 동일 |

### 5.3. 수집기 구현 설계

```python
"""FRED 기반 경제지표 수집기 (FinanceDataReader 경유)."""

SOURCE = "FRED"

def collect_daily_prices(symbol: str, start: str, end: str) -> pd.DataFrame:
    """FRED 경제지표를 수집해 daily_price 적재용 DataFrame으로 반환.

    FDR 호출 시 'FRED:{symbol}' 형태로 조합한다.
    반환 컬럼: trade_dt, close_price (나머지 OHLCV는 None).
    """
    fdr_symbol = f"FRED:{symbol}"
    raw = fdr.DataReader(fdr_symbol, start, end)
    # Close 컬럼을 close_price로 매핑
    # open_price, high_price, low_price, volume, trade_amount, change_rate = None
```

- `fdr_collector.py`와 동일한 `_COLUMN_MAP` 패턴 적용.
- FRED 데이터에는 `Close` 컬럼만 존재하므로, 나머지는 `None`으로 보강.
- `NaN → None` 변환 (`.cursorrules` 준수).

---

## 6. 수집 배치 연동

### 6.1. `collect.py` 변경

`_COLLECTORS` 딕셔너리에 `"FRED"` 매핑 추가:

```python
from src.collectors import fdr_collector, fred_collector, yahoo_collector

_COLLECTORS: dict[str, Callable] = {
    "FDR":   fdr_collector.collect_daily_prices,
    "YAHOO": yahoo_collector.collect_daily_prices,
    "FRED":  fred_collector.collect_daily_prices,
}
```

- 기존 `source` 기반 분기 구조를 그대로 활용.
- 종목마스터에 `source='FRED'`로 등록된 종목은 자동으로 `fred_collector`로 수집.
- **기존 수집 로직 변경 없음** — 매핑 1줄 추가.

### 6.2. 실행 방법 (변경 없음)

```bash
# 전체 종목(기존 16 + FRED 10) 최근 1개월
uv run python -m src.collect

# FRED 특정 종목만 (symbol_id 지정)
uv run python -m src.collect --symbol-id 17 --from-date 19500101 --to-date 20260715

# 전체 종목 장기 백필
uv run python -m src.collect --from-date 20200101 --to-date 20260715
```

---

## 7. 종목 시드 확장 (`symbols_seed.py`)

기존 `SYMBOLS` 리스트에 FRED 10종목 추가. 신규 컬럼(`data_frequency`, `category`) 포함.

```python
# 기존 16종: data_frequency, category 추가
{"source": "FDR", "symbol": "KS11", ..., "data_frequency": "Daily", "category": "Market"},

# FRED 10종 추가
{"source": "FRED", "symbol": "FEDFUNDS", "symbol_nm": "Fed 기준금리",
 "remark": "Effective Federal Funds Rate", "data_frequency": "Monthly", "category": "FRED"},
...
```

- `get_or_create_symbol()` 함수에 `data_frequency`, `category` 파라미터 추가.
- 기존 종목은 `(source, symbol)` 기준으로 이미 존재하므로 건너뜀 (멱등).
- 신규 FRED 종목만 새로 채번.

---

## 8. 관련 서비스 변경

### 8.1. `init_db.py` — `get_or_create_symbol()` 확장

```python
def get_or_create_symbol(
    session: Session, source: str, symbol: str, symbol_nm: str,
    remark: str | None = None,
    data_frequency: str | None = None,
    category: str | None = None,
) -> int:
```

### 8.2. `symbol_service.py` — `_to_dict()` 확장

```python
def _to_dict(row: SymbolMaster) -> dict:
    return {
        # ... 기존 필드 ...
        "data_frequency": row.data_frequency,
        "category": row.category,
    }
```

- `create_symbol()`, `update_symbol()`에도 `data_frequency`, `category` 파라미터 추가.

### 8.3. Admin 화면 (`views/admin_symbols.py`)

- 입력 폼에 `data_frequency` (selectbox: Daily/Weekly/Monthly/Yearly/Irregular) 추가.
- 입력 폼에 `category` (text_input) 추가.
- 목록 테이블에 `data_frequency`, `category` 컬럼 표시.

---

## 9. 디렉토리 구조 (변경분)

```
src/
├── collectors/
│   ├── fdr_collector.py       # (변경 없음)
│   ├── yahoo_collector.py     # (변경 없음)
│   └── fred_collector.py      # [신규] FRED 경제지표 수집기
├── db/
│   └── models.py              # [변경] SymbolMaster에 data_frequency, category 추가
├── collect.py                 # [변경] _COLLECTORS에 "FRED" 추가 (1줄)
├── symbols_seed.py            # [변경] FRED 10종목 + 신규 컬럼 추가
├── init_db.py                 # [변경] get_or_create_symbol() 파라미터 확장
└── migrate_v2.py              # [신규] ALTER TABLE 마이그레이션 스크립트

dashboard/
├── services/
│   └── symbol_service.py      # [변경] _to_dict, create/update에 신규 컬럼
└── views/
    └── admin_symbols.py       # [변경] 입력 폼에 data_frequency, category 추가
```

---

## 10. 단계별 실행 계획

### 단계 0. 스키마 변경 (데이터 유실 방지)

- [ ] `src/db/models.py` — `SymbolMaster`에 `data_frequency`, `category` 컬럼 추가 (nullable)
- [ ] `src/migrate_v2.py` 작성 — ALTER TABLE + 기존 데이터 보정
  - ALTER TABLE ADD COLUMN IF NOT EXISTS
  - 기존 16종목 `data_frequency='Daily'` 설정
  - 기존 종목 `category` 분류 설정 (Market/Stock)
- [ ] 마이그레이션 실행 및 검증: `uv run python -m src.migrate_v2`

### 단계 1. FRED 수집기 작성

- [ ] `src/collectors/fred_collector.py` 작성
  - `fdr.DataReader('FRED:{symbol}', start, end)` 호출
  - `Close` → `close_price` 매핑, 나머지 OHLCV `None`
  - 공통 인터페이스 `collect_daily_prices(symbol, start, end) → DataFrame`
- [ ] 단독 임포트 검증: `uv run python -c "from src.collectors.fred_collector import collect_daily_prices"`

### 단계 2. 수집 배치 연동

- [ ] `src/collect.py` — `_COLLECTORS`에 `"FRED": fred_collector.collect_daily_prices` 추가
- [ ] `src/init_db.py` — `get_or_create_symbol()`에 `data_frequency`, `category` 파라미터 추가

### 단계 3. 종목 시드 확장

- [ ] `src/symbols_seed.py` — FRED 10종목 추가 + 기존 종목에 `data_frequency`/`category` 반영
- [ ] 시드 실행 및 검증: `uv run python -m src.symbols_seed`
- [ ] `symbol_master` 26종(기존 16 + FRED 10) 확인

### 단계 4. 관련 서비스·화면 변경

- [ ] `dashboard/services/symbol_service.py` — `_to_dict`, `create_symbol`, `update_symbol` 확장
- [ ] `dashboard/views/admin_symbols.py` — 입력 폼에 `data_frequency`, `category` 추가
- [ ] 로컬 기동 확인: Admin Symbols 화면에서 신규 컬럼 조회·수정 동작

### 단계 5. 수집 검증

- [ ] FRED 단일 종목 수집 테스트: `uv run python -m src.collect --symbol-id {FEDFUNDS_ID} --from-date 20200101`
- [ ] 전체 종목 일괄 수집: `uv run python -m src.collect`
- [ ] 대상 26종목 / 성공 26종 / 실패 0종 확인
- [ ] `logs/finsight_*.log` 요약 로그 확인
- [ ] 재실행 시 멱등성 확인

---

## 11. 완료 기준 (Definition of Done)

- [ ] `symbol_master`에 `data_frequency`, `category` 컬럼이 추가되고 기존 데이터가 보존된다.
- [ ] 기존 16종목에 `data_frequency='Daily'`, 적절한 `category` 값이 설정된다.
- [ ] FRED 10종목이 종목마스터에 등록된다.
- [ ] `uv run python -m src.collect` 실행 시 26종 전체가 수집·적재된다.
- [ ] FRED 데이터가 `daily_price.close_price`에 정상 적재된다 (OHLCV는 NULL).
- [ ] 재실행 시 중복 적재 없이 멱등성이 유지된다.
- [ ] Admin Symbols 화면에서 `data_frequency`, `category`를 조회·수정할 수 있다.
- [ ] 기존 FDR/YAHOO 수집에 영향이 없다.

---

## 12. 리스크 및 고려사항

| 항목 | 내용 | 대응 |
| --- | --- | --- |
| ALTER TABLE 데이터 유실 | 컬럼 추가 시 기존 행 영향 | nullable 컬럼 추가 → 기존 행은 NULL, 이후 UPDATE로 보정 |
| Alembic 미사용 | 스키마 버전 관리 부재 | 1회성 `migrate_v2.py` 스크립트로 대응. `IF NOT EXISTS`로 멱등 실행 |
| FDR FRED 지원 범위 | 일부 FRED 심볼이 FDR에서 미지원될 수 있음 | 수집 실행 시 종목별 성공/실패 확인, 미지원 시 대안 검토 |
| Monthly 데이터 일자 표현 | 월간 데이터의 `trade_dt`는 해당 월의 특정일(1일 또는 마지막 거래일) | FRED 원천 그대로 적재, 일자 해석은 시각화 단계에서 처리 |
| 대량 백필 | 1950년대~현재 데이터 조회 시 수만 건 | `BATCH_SIZE=500` 기존 chunk 처리, `get_series` 캐시 활용 |
| `create_all` 제약 | SQLAlchemy `create_all`은 기존 테이블에 컬럼 추가 불가 | `migrate_v2.py`에서 raw SQL `ALTER TABLE` 사용 |
| Admin 화면 호환 | 신규 컬럼이 폼에 없으면 NULL 저장 | Admin 폼에 신규 필드 추가, 기존 로직 영향 없음 (nullable) |

---

## 13. 의존성

현재 `requirements.txt`에 추가 패키지 불필요. FinanceDataReader가 FRED 데이터 조회를 지원한다.

```
# 백엔드 (pyproject.toml / uv.lock)
finance-datareader    # FRED 지원 포함
yfinance              # (기존, 변경 없음)

# 프런트엔드 (requirements.txt)
# 변경 없음
```
